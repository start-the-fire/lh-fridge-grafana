import os
import html
import smtplib
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from croniter import croniter
from influxdb_client import InfluxDBClient
from influxdb_client.rest import ApiException
from matplotlib.backends.backend_pdf import PdfPages


def required_env(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing environment variable: {name}")
    return value


INFLUX_URL = required_env("INFLUX_URL")
INFLUX_TOKEN = required_env("INFLUX_TOKEN")
INFLUX_ORG = required_env("INFLUX_ORG")
INFLUX_BUCKET = required_env("INFLUX_BUCKET")
EXPORT_FREQUENCY = os.getenv("EXPORT_FREQUENCY", "monthly").lower()
EXPORT_CRON = os.getenv("EXPORT_CRON", "0 3 1 * *")
EXPORT_EMAIL_FROM = required_env("EXPORT_EMAIL_FROM")
EXPORT_EMAIL_TO = required_env("EXPORT_EMAIL_TO")
SMTP_SERVER = required_env("SMTP_SERVER")
SMTP_USERNAME = required_env("SMTP_USERNAME")
SMTP_PASSWORD = required_env("SMTP_PASSWORD")
EXPORT_OUTPUT_DIR = os.getenv("EXPORT_OUTPUT_DIR", "/tmp")

try:
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
except ValueError as exc:
    raise ValueError("SMTP_PORT must be an integer") from exc

if EXPORT_FREQUENCY not in {"monthly", "quarterly", "yearly", "all"}:
    raise ValueError("EXPORT_FREQUENCY must be monthly, quarterly, yearly, or all")
if SMTP_PORT <= 0 or SMTP_PORT > 65535:
    raise ValueError("SMTP_PORT must be between 1 and 65535")
if not croniter.is_valid(EXPORT_CRON):
    raise ValueError(f"Invalid EXPORT_CRON expression: {EXPORT_CRON}")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()


def utc_iso(value):
    return value.isoformat().replace("+00:00", "Z")


def add_months(value, months):
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return value.replace(year=year, month=month)


def report_period(now=None):
    end = (now or datetime.now(timezone.utc)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    if EXPORT_FREQUENCY == "all":
        return None, end
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}[EXPORT_FREQUENCY]
    start = add_months(end, -months)
    return start, end


def report_name(start, end):
    if EXPORT_FREQUENCY == "all":
        return "fridge_export_all"
    if EXPORT_FREQUENCY == "monthly":
        return f"fridge_export_{start:%Y_%m}"
    if EXPORT_FREQUENCY == "yearly":
        return f"fridge_export_{start:%Y}"
    quarter = ((start.month - 1) // 3) + 1
    return f"fridge_export_{start:%Y}_Q{quarter}"


def temperature_average(df):
    if "_field" not in df or "_value" not in df:
        return None
    values = pd.to_numeric(
        df.loc[df["_field"] == "temp_displayed", "_value"], errors="coerce"
    ).dropna()
    return float(values.mean()) if not values.empty else None


def create_report_pdf(df, table_df, pdf_path, title, average):
    if "_field" in df.columns:
        temperature = df[df["_field"] == "temp_displayed"].copy()
    else:
        temperature = df.iloc[0:0].copy()
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
            axis.plot(
                temperature["_time"],
                temperature["_value"],
                marker=".",
                linewidth=1,
                label="temp_displayed",
            )
            setpoint = df[df["_field"] == "temp_setpoint"].copy()
            setpoint["_time"] = pd.to_datetime(setpoint["_time"], errors="coerce")
            setpoint["_value"] = pd.to_numeric(setpoint["_value"], errors="coerce")
            setpoint = setpoint.dropna(subset=["_time", "_value"])
            if not setpoint.empty:
                axis.plot(
                    setpoint["_time"],
                    setpoint["_value"],
                    marker=".",
                    linewidth=1,
                    label="temp_setpoint",
                )
            if average is not None:
                axis.axhline(
                    average,
                    color="tab:red",
                    linestyle="--",
                    linewidth=1,
                    label=f"average: {average:.2f}",
                )
            axis.set_ylabel("Temperature")
            axis.set_xlabel("UTC time")
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            figure.autofmt_xdate()
            axis.grid(True, alpha=0.3)
            axis.legend()
        average_text = "n/a" if average is None else f"{average:.2f}"
        axis.set_title(f"{title} - average displayed temperature: {average_text}")
        figure.tight_layout()
        pdf.savefig(figure)
        plt.close(figure)

        table_df = table_df.fillna("")
        if table_df.empty:
            table_df = pd.DataFrame([{"message": "No data returned"}])
        columns = list(table_df.columns)
        rows_per_page = 30
        for offset in range(0, len(table_df), rows_per_page):
            page_rows = table_df.iloc[offset : offset + rows_per_page]
            figure, axis = plt.subplots(figsize=(11.69, 8.27))
            axis.axis("off")
            table = axis.table(
                cellText=page_rows.astype(str).values,
                colLabels=columns,
                bbox=[0, 0, 1, 0.91],
                cellLoc="left",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(6)
            table.scale(1, 1.4)
            figure.suptitle(
                f"{title} - values (rows {offset + 1}-{offset + len(page_rows)})",
                y=0.98,
            )
            figure.tight_layout()
            pdf.savefig(figure)
            plt.close(figure)


def send_email(csv_path, pdf_path, csv_name, pdf_name, average, model, serial, start, end):
    msg = EmailMessage()
    frequency_title = EXPORT_FREQUENCY.capitalize()
    start_text = f"{start.day} {start:%B %Y}"
    end_text = f"{end.day} {end:%B %Y}"
    date_range = f"{start_text} - {end_text}"
    msg["From"] = EXPORT_EMAIL_FROM
    msg["To"] = EXPORT_EMAIL_TO
    average_text = "not available" if average is None else f"{average:.2f}"
    model_text = model or "unknown model"
    serial_text = serial or "unknown"
    msg["Subject"] = (
        f"{frequency_title} Temperature Report: {start:%Y-%m-%d} to {end:%Y-%m-%d}"
    )
    msg.set_content(
        "Please find attached the temperature monitoring report for the following "
        "refrigeration unit:\n"
        f"Device: Liebherr {model_text}\n"
        f"Serial number: {serial_text}\n"
        f"Reporting period: {date_range}\n"
        f"Average displayed temperature: {average_text} °C\n\n"
        "The attached files contain the detailed temperature data in CSV format as "
        "well as the corresponding PDF report for the reporting period.\n\n"
        "This email and the attached report have been generated and sent automatically "
        "by the temperature monitoring system.\n"
        "Please do not reply to this email."
    )
    msg.add_alternative(
        f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #263238; line-height: 1.5;">
            <p>Please find attached the temperature monitoring report for the following
            refrigeration unit:</p>
            <table style="border-collapse: collapse; margin: 16px 0;">
              <tr><td style="padding: 4px 20px 4px 0;"><strong>Device:</strong></td>
                  <td style="padding: 4px 0;">Liebherr {html.escape(model_text)}</td></tr>
              <tr><td style="padding: 4px 20px 4px 0;"><strong>Serial number:</strong></td>
                  <td style="padding: 4px 0;">{html.escape(serial_text)}</td></tr>
              <tr><td style="padding: 4px 20px 4px 0;"><strong>Reporting period:</strong></td>
                  <td style="padding: 4px 0;">{html.escape(date_range)}</td></tr>
              <tr><td style="padding: 4px 20px 4px 0;"><strong>Average displayed temperature:</strong></td>
                  <td style="padding: 4px 0;">{html.escape(average_text)} °C</td></tr>
            </table>
            <p>The attached files contain the detailed temperature data in CSV format as
            well as the corresponding PDF report for the reporting period.</p>
            <p style="color: #607d8b; font-size: 0.9em;">This email and the attached
            report have been generated and sent automatically by the temperature
            monitoring system.<br>Please do not reply to this email.</p>
          </body>
        </html>
        """,
        subtype="html",
    )

    for filepath, filename, subtype in (
        (csv_path, csv_name, "csv"),
        (pdf_path, pdf_name, "pdf"),
    ):
        with open(filepath, "rb") as attachment:
            msg.add_attachment(
                attachment.read(), maintype="application" if subtype == "pdf" else "text",
                subtype=subtype, filename=filename
            )

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(msg)
    print("Email sent.", flush=True)


def export_report(now=None):
    start, end = report_period(now)
    query_start = "0" if start is None else utc_iso(start)
    basename = report_name(start or end, end)
    csv_name = f"{basename}.csv"
    pdf_name = f"{basename}.pdf"
    csv_path = os.path.join(EXPORT_OUTPUT_DIR, csv_name)
    pdf_path = os.path.join(EXPORT_OUTPUT_DIR, pdf_name)
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {query_start}, stop: {utc_iso(end)})
      |> filter(fn: (r) => r._measurement == "fridge_zone_state")
    '''

    print("Running export query...", flush=True)
    tables = query_api.query(query)
    rows = [record.values for table in tables for record in table.records]
    df = pd.DataFrame(rows).drop(
        columns=["_start", "_stop", "result", "table"], errors="ignore"
    )
    if start is None and not df.empty and "_time" in df.columns:
        timestamps = pd.to_datetime(df["_time"], errors="coerce", utc=True).dropna()
        if not timestamps.empty:
            start = timestamps.min().to_pydatetime()
    if start is None:
        start = end
    average = temperature_average(df)
    serials = df.get("device_serial", pd.Series(dtype=str)).dropna().unique()
    serial = str(serials[0]) if len(serials) else None
    models = df.get("model", pd.Series(dtype=str)).dropna().unique()
    model = str(models[0]) if len(models) else None
    if "_field" in df.columns:
        report_df = df[
            df["_field"].isin(["temp_displayed", "temp_setpoint"])
        ].copy()
    else:
        report_df = pd.DataFrame(columns=["_time", "_value", "_field"])
    report_df["_value"] = pd.to_numeric(report_df["_value"], errors="coerce")
    csv_df = (
        report_df.pivot_table(
            index="_time", columns="_field", values="_value", aggfunc="last"
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    csv_df = csv_df.reindex(
        columns=["_time", "temp_displayed", "temp_setpoint"], fill_value=""
    ).sort_values("_time")
    os.makedirs(EXPORT_OUTPUT_DIR, exist_ok=True)
    csv_df.to_csv(csv_path, index=False)
    create_report_pdf(df, csv_df, pdf_path, basename, average)
    send_email(csv_path, pdf_path, csv_name, pdf_name, average, model, serial, start, end)
    return csv_path, pdf_path


def run_once():
    paths = None
    try:
        paths = export_report()
    finally:
        if paths:
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)


def main():
    now = datetime.now(timezone.utc)
    next_run = croniter(EXPORT_CRON, now).get_next(datetime).replace(tzinfo=timezone.utc)
    last_report_end = None
    print(f"Exporter service running; next export: {next_run.isoformat()}", flush=True)
    try:
        while True:
            now = datetime.now(timezone.utc)
            if now >= next_run:
                report_end = report_period(now)[1]
                period_is_due = (
                    EXPORT_FREQUENCY in {"monthly", "all"}
                    or (EXPORT_FREQUENCY == "quarterly" and now.month in (1, 4, 7, 10))
                    or (EXPORT_FREQUENCY == "yearly" and now.month == 1)
                )
                if period_is_due and report_end != last_report_end:
                    try:
                        run_once()
                    except (ApiException, OSError, RuntimeError, smtplib.SMTPException, ValueError) as exc:
                        print(f"Export failed; will retry: {exc}", flush=True)
                        time.sleep(60)
                        continue
                    last_report_end = report_end
                next_run = croniter(EXPORT_CRON, next_run).get_next(datetime)
                next_run = next_run.replace(tzinfo=timezone.utc)
                print(f"Next export: {next_run.isoformat()}", flush=True)
            time.sleep(min(60, max(1, (next_run - now).total_seconds())))
    except KeyboardInterrupt:
        print("Exporter stopped.", flush=True)
    finally:
        client.close()


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        try:
            run_once()
        finally:
            client.close()
    elif len(sys.argv) > 1:
        raise SystemExit("Usage: python export.py [--test]")
    else:
        main()
