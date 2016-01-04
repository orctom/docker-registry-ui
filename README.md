# docker-registry-ui

## docker run
```
docker run \
    -d \
    --name docker-registry-ui \
    -p 8080:8080 \
    -e REGISTRY_URL=http://172.17.0.1:5000 \
    orctom/docker-registry-ui
```

## docker-compose
[docker-compose.yml](https://github.com/orctom/docker/blob/master/registry/docker-compose.yml)
