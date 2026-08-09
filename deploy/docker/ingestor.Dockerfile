FROM golang:1.26.5-alpine AS builder
WORKDIR /src
COPY services/ingestor/go.mod services/ingestor/go.sum* ./
RUN go mod download
COPY services/ingestor/ .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/ingestor ./cmd/ingestor

FROM alpine:3.22
RUN addgroup -S crisismesh && adduser -S -G crisismesh crisismesh && apk add --no-cache ca-certificates
COPY --from=builder /out/ingestor /usr/local/bin/ingestor
USER crisismesh
ENTRYPOINT ["/usr/local/bin/ingestor"]

