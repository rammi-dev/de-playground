{{/*
Generate the full name of the resource.
*/}}
{{- define "minio-helm-chart.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "minio.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- .Release.Name }}-minio
{{- else -}}
{{- .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "minio.labels" -}}
app: {{ include "minio.fullname" . }}
chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
release: {{ .Release.Name }}
heritage: {{ .Release.Service }}
{{- end -}}