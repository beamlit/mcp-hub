FILENAME=$1.yaml
IS_CHECKPOINT=false

file_name=$(basename $FILENAME | sed 's/.yaml//g')
echo "Testing $file_name"
echo "Testing $server"
go run main.go test -c hack/mcp-agent/output/  -m $file_name  --debug
GO_EXIT_CODE=$?
if [ $GO_EXIT_CODE -ne 0 ]; then
    echo "Error: go run command failed with exit code $GO_EXIT_CODE"
    docker ps -a | grep $file_name | awk '{print $1}' | xargs docker stop
    docker ps -a | grep $file_name | awk '{print $1}' | xargs docker rm
    # docker image rm docker.io/library/$file_name:latest # remove the image
    echo "Failed to run the following servers: $server"
    exit 1
fi

npx tsx --tsconfig=web-search/tsconfig.json web-search/client.ts
NPX_EXIT_CODE=$?
if [ $NPX_EXIT_CODE -ne 0 ]; then
    echo "Error: npx tsx command failed with exit code $NPX_EXIT_CODE"
    docker ps -a | grep $file_name | awk '{print $1}' | xargs docker stop
    # docker image rm docker.io/library/$file_name:latest # remove the image
    echo "Failed to run the following servers: $server"
    go run main.go dockerrun -c hack/mcp-agent/output/  -m $file_name  --debug
    exit 1
fi
docker ps -a | grep $file_name | awk '{print $1}' | xargs docker stop
# docker image rm docker.io/library/$file_name:latest # remove the image
if [ $? -ne 0 ]; then
    echo "Warning: Failed to remove docker image for $server"
fi