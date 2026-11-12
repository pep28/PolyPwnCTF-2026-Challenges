FROM debian:forky@sha256:49c219ade93d7c11635c0d57e735ed82339a503a4376cd6957046c2bd4e5905b

RUN apt update

# setup zig. we need debian because of glibc
ENV ZIG_VERSION=0.15.2
RUN apt install -y curl xz-utils python3
RUN \
    curl -LO https://ziglang.org/download/${ZIG_VERSION}/zig-`uname -m`-linux-${ZIG_VERSION}.tar.xz && \
    tar xf ./zig-*.tar.xz && \
    rm *.tar.xz && \
    mv ./zig-* /zig

COPY . /app
WORKDIR /app

# just in case
RUN rm -rf zig-out .zig-cache

# first run will fail
RUN /zig/zig build -Doptimize=ReleaseFast || true
RUN /zig/zig build -Doptimize=ReleaseFast

FROM alpine:edge@sha256:020dfcbaaf4cc1078bf2d9c7ba31a8466e334061dcd2f248001d68f79e52c000
RUN apk add libc6-compat
COPY --from=0 /app/zig-out/bin/server /server
EXPOSE 80
CMD ["/server"]
