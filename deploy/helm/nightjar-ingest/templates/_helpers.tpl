{{- define "nightjar-ingest.name" -}}
nightjar-ingest
{{- end -}}

{{- define "nightjar-ingest.labels" -}}
app.kubernetes.io/name: {{ include "nightjar-ingest.name" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "nightjar-ingest.image" -}}
{{ .Values.image.repository }}:{{ .Values.image.tag }}
{{- end -}}
