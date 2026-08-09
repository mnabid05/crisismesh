FROM golang:1.26.5-alpine AS builder
WORKDIR /src
COPY services/api/go.mod services/api/go.sum* ./
RUN go mod download
COPY services/api/ .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/api ./cmd/server

FROM alpine:3.22
RUN addgroup -S crisismesh && adduser -S -G crisismesh crisismesh && apk add --no-cache ca-certificates
COPY --from=builder /out/api /usr/local/bin/api
USER crisismesh
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/api"]

