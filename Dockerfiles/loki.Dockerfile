FROM grafana/loki:latest

CMD ["-config.file=/etc/loki/local-config.yaml"]