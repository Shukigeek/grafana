FROM grafana/promtail:2.9.0

COPY promtail-config.yaml /etc/promtail/config.yaml

CMD ["-config.file=/etc/promtail/config.yaml"]