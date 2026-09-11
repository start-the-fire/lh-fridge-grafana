from __future__ import annotations

import html
import tempfile
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import aiosmtplib
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from influxdb_client import InfluxDBClient
from matplotlib.backends.backend_pdf import PdfPages

from .core.config import Settings


def report_period(frequency: str, now: datetime | None = None) -> tuple[datetime | None, datetime]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today = current.replace(hour=0, minute=0, second=0, microsecond=0)
    if frequency == "all":
        return None, current.replace(minute=0, second=0, microsecond=0)
    if frequency == "daily":
        return today - timedelta(days=1), today
    if frequency == "weekly":
        this_week_start = today - timedelta(days=today.weekday())
        return this_week_start - timedelta(days=7), this_week_start
    if frequency == "monthly":
        this_month_start = today.replace(day=1)
        return _add_months(this_month_start, -1), this_month_start
    if frequency == "quarterly":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        this_quarter_start = today.replace(month=quarter_start_month, day=1)
        return _add_months(this_quarter_start, -3), this_quarter_start
    if frequency == "yearly":
        this_year_start = today.replace(month=1, day=1)
        return this_year_start.replace(year=this_year_start.year - 1), this_year_start
    return report_period("monthly", current)


def next_report_time(frequency: str, now: datetime | None = None) -> datetime:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today = current.replace(hour=0, minute=0, second=0, microsecond=0)
    if frequency == "daily":
        candidate = today + timedelta(days=1)
    elif frequency == "all":
        candidate = today + timedelta(days=1)
    elif frequency == "weekly":
        candidate = today - timedelta(days=today.weekday()) + timedelta(days=7)
    elif frequency == "quarterly":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        candidate = _add_months(today.replace(month=quarter_start_month, day=1), 3)
    elif frequency == "yearly":
        candidate = today.replace(month=1, day=1, year=today.year + 1)
    else:
        candidate = _add_months(today.replace(day=1), 1)
    return candidate if current < candidate else next_report_time(frequency, candidate + timedelta(seconds=1))


def report_period_key(frequency: str, now: datetime | None = None) -> str:
    start, end = report_period(frequency, now)
    start_value = "0" if start is None else start.isoformat()
    return f"{frequency}:{start_value}:{end.isoformat()}"


def next_report_due(frequency: str, last_period_key: str | None, now: datetime | None = None, requested_at: str | None = None) -> bool:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if frequency == "all":
        if not requested_at:
            return False
        try:
            requested = datetime.fromisoformat(requested_at)
            if requested.tzinfo is None:
                requested = requested.replace(tzinfo=timezone.utc)
        except ValueError:
            return False
        return current >= next_report_time("all", requested) and last_period_key != report_period_key(frequency, current)
    scheduled_at = report_period(frequency, current)[1]
    return current >= scheduled_at and last_period_key != report_period_key(frequency, current)


def _add_months(value: datetime, months: int) -> datetime:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return value.replace(year=year, month=month, day=day)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _report_name(frequency: str, start: datetime, end: datetime) -> str:
    if frequency == "daily":
        return f"tempverity_report_{start:%Y_%m_%d}"
    if frequency == "all":
        return f"tempverity_report_all_until_{end:%Y_%m_%d_%H%M}"
    if frequency == "weekly":
        return f"tempverity_report_week_{start:%Y_%m_%d}"
    if frequency == "quarterly":
        quarter = ((start.month - 1) // 3) + 1
        return f"tempverity_report_{start:%Y}_Q{quarter}"
    if frequency == "yearly":
        return f"tempverity_report_{start:%Y}"
    return f"tempverity_report_{start:%Y_%m}"


def _temperature_average(df: pd.DataFrame) -> float | None:
    if "_field" not in df or "_value" not in df:
        return None
    values = pd.to_numeric(df.loc[df["_field"] == "temp_displayed", "_value"], errors="coerce").dropna()
    return float(values.mean()) if not values.empty else None


def _create_report_pdf(df: pd.DataFrame, table_df: pd.DataFrame, pdf_path: Path, title: str, average: float | None) -> None:
    temperature = df[df["_field"] == "temp_displayed"].copy() if "_field" in df.columns else df.iloc[0:0].copy()
    if not temperature.empty:
        temperature["_time"] = pd.to_datetime(temperature["_time"], errors="coerce")
        temperature["_value"] = pd.to_numeric(temperature["_value"], errors="coerce")
        temperature = temperature.dropna(subset=["_time", "_value"])

    with PdfPages(pdf_path) as pdf:
        figure, axis = plt.subplots(figsize=(11.69, 8.27))
        if temperature.empty:
            axis.text(0.5, 0.5, "No temperature data available", ha="center", va="center")
            axis.set_axis_off()
        else:
            if "device_name" not in temperature.columns:
                temperature["device_name"] = temperature.get("device_serial", "Device")
            if "zone" not in temperature.columns:
                temperature["zone"] = "0"
            for label, group in temperature.groupby(["device_name", "zone"]):
                axis.plot(group["_time"], group["_value"], marker=".", linewidth=1, label=" | ".join(str(item) for item in (label if isinstance(label, tuple) else (label,))))
            average_text = "n/a" if average is None else f"{average:.2f}"
            if average is not None:
                axis.axhline(average, color="tab:red", linestyle="--", linewidth=1, label=f"average: {average_text}")
            axis.set_ylabel("Temperature °C")
            axis.set_xlabel("UTC time")
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            figure.autofmt_xdate()
            axis.grid(True, alpha=0.3)
            axis.legend()
        axis.set_title(title)
        figure.tight_layout()
        pdf.savefig(figure)
        plt.close(figure)

        table_df = table_df.fillna("")
        if table_df.empty:
            table_df = pd.DataFrame([{"message": "No data returned"}])
        columns = list(table_df.columns)
        for offset in range(0, len(table_df), 30):
            page_rows = table_df.iloc[offset : offset + 30]
            figure, axis = plt.subplots(figsize=(11.69, 8.27))
            axis.axis("off")
            table = axis.table(cellText=page_rows.astype(str).values, colLabels=columns, bbox=[0, 0, 1, 0.91], cellLoc="left")
            table.auto_set_font_size(False)
            table.set_fontsize(6)
            table.scale(1, 1.4)
            figure.suptitle(f"{title} - values", y=0.98)
            figure.tight_layout()
            pdf.savefig(figure)
            plt.close(figure)


async def send_report(settings: Settings, smtp: dict[str, Any], report_settings: dict[str, Any], now: datetime | None = None) -> dict[str, object]:
    if not settings.influx_enabled or not all([settings.influx_url, settings.influx_org, settings.influx_bucket, settings.influx_token]):
        return {"ok": False, "message": "InfluxDB is not configured"}
    recipients = report_settings.get("recipients", [])
    if isinstance(recipients, str):
        recipients = [item.strip() for item in recipients.split(",")]
    recipients = [str(item).strip() for item in recipients if str(item).strip()]
    if not recipients:
        return {"ok": False, "message": "No report recipient is configured"}
    if not isinstance(smtp, dict) or not smtp.get("enabled") or not smtp.get("host"):
        return {"ok": False, "message": "SMTP sender settings are not enabled or incomplete"}

    frequency = str(report_settings.get("frequency", "monthly"))
    start, end = report_period(frequency, now)
    query_start = "0" if start is None else _utc_iso(start)
    query = f'''
    from(bucket: "{settings.influx_bucket}")
      |> range(start: {query_start}, stop: {_utc_iso(end)})
      |> filter(fn: (r) => r._measurement == "fridge_zone_state")
    '''
    with InfluxDBClient(url=settings.influx_url, token=settings.influx_token, org=settings.influx_org) as client:
        tables = client.query_api().query(query)
    rows = [record.values for table in tables for record in table.records]
    df = pd.DataFrame(rows).drop(columns=["_start", "_stop", "result", "table"], errors="ignore")
    average = _temperature_average(df)

    if "_field" in df.columns:
        report_df = df[df["_field"].isin(["temp_displayed", "temp_setpoint"])].copy()
    else:
        report_df = pd.DataFrame(columns=["_time", "device_name", "zone", "_field", "_value"])
    report_df["_value"] = pd.to_numeric(report_df["_value"], errors="coerce")
    index_columns = [column for column in ["_time", "device_name", "zone"] if column in report_df.columns]
    csv_df = report_df.pivot_table(index=index_columns or ["_time"], columns="_field", values="_value", aggfunc="last").reset_index().rename_axis(None, axis=1)
    csv_df = csv_df.sort_values(index_columns or ["_time"])

    if start is None and not df.empty and "_time" in df.columns:
        timestamps = pd.to_datetime(df["_time"], errors="coerce", utc=True).dropna()
        if not timestamps.empty:
            start = timestamps.min().to_pydatetime()
    start = start or end
    basename = _report_name(frequency, start, end)
    with tempfile.TemporaryDirectory() as directory:
        csv_path = Path(directory) / f"{basename}.csv"
        pdf_path = Path(directory) / f"{basename}.pdf"
        csv_df.to_csv(csv_path, index=False)
        average_text = "n/a" if average is None else f"{average:.2f}"
        title = f"{basename} - average displayed temperature: {average_text}"
        _create_report_pdf(df, csv_df, pdf_path, title, average)
        message = EmailMessage()
        message["From"] = str(smtp.get("from", "alerts@example.invalid"))
        message["To"] = ", ".join(recipients)
        message["Subject"] = f"TempVerity {frequency.capitalize()} Temperature Report"
        date_range = f"{start:%Y-%m-%d %H:%M UTC} - {end:%Y-%m-%d %H:%M UTC}"
        message.set_content(f"Attached is the TempVerity temperature report.\n\nReporting period: {date_range}\nAverage displayed temperature: {average_text} °C\n")
        message.add_alternative(f"<html><body><p>Attached is the TempVerity temperature report.</p><table><tr><td><strong>Reporting period:</strong></td><td>{html.escape(date_range)}</td></tr><tr><td><strong>Average displayed temperature:</strong></td><td>{html.escape(average_text)} °C</td></tr></table></body></html>", subtype="html")
        for path, subtype in ((csv_path, "csv"), (pdf_path, "pdf")):
            message.add_attachment(path.read_bytes(), maintype="application" if subtype == "pdf" else "text", subtype=subtype, filename=path.name)
        security = str(smtp.get("security", "STARTTLS")).upper()
        await aiosmtplib.send(message, hostname=str(smtp["host"]), port=int(smtp.get("port", 587)), username=str(smtp.get("username", "")) or None, password=str(smtp.get("password", "")) or None, start_tls=security == "STARTTLS", use_tls=security in {"TLS", "SSL", "TLS/SSL"}, timeout=float(smtp.get("timeout", 30)))
    return {"ok": True, "message": "Report email sent", "sentAt": end.isoformat(), "recipients": recipients}
