apiVersion: 1

datasources:
  - name: InfluxDB
    uid: influxdb
    type: influxdb
    access: proxy
    url: ${INFLUX_URL}
    isDefault: true
    editable: false
    jsonData:
      version: Flux
      organization: ${INFLUX_ORG}
      defaultBucket: ${INFLUX_BUCKET}
      httpMode: POST
    secureJsonData:
      token: ${INFLUX_TOKEN}
