FROM golang:alpine AS build
ENV CGO_ENABLED=0
ENV GOOS=linux
WORKDIR /src
COPY . .
RUN go build -o /happiness .
FROM scratch AS bin
COPY --from=build /happiness /
CMD [ "/happiness" ]
