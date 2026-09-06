FROM grafana/grafana:13.2.1

USER root

RUN apk add --no-cache gettext

COPY templates /etc/grafana-templates
COPY entrypoint.sh /usr/local/bin/grafana-entrypoint.sh
RUN chmod 755 /usr/local/bin/grafana-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/grafana-entrypoint.sh"]
