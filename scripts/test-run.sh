CHECKPOINT="rest-to-postman-mcp.yaml"
IS_CHECKPOINT=false
FAIL_LIST_BUILD=()
FAIL_LIST_RUN=()
for server in $(ls hack/mcp-agent/output); do
    file_name=$(basename $server | sed 's/.yaml//g')
    echo "Testing $file_name"
    echo "Testing $server"
    go run main.go test -c hack/mcp-agent/output/  -m $file_name  --debug
    GO_EXIT_CODE=$?
    if [ $GO_EXIT_CODE -ne 0 ]; then
        echo "Error: go run command failed with exit code $GO_EXIT_CODE"
        docker ps -a | grep $file_name | awk '{print $1}' | xargs docker stop
        docker ps -a | grep $file_name | awk '{print $1}' | xargs docker rm
        docker image rm docker.io/library/$file_name:latest # remove the image
        FAIL_LIST_BUILD+=($server)
        continue
    fi

    npx tsx --tsconfig=web-search/tsconfig.json web-search/client.ts
    NPX_EXIT_CODE=$?
    if [ $NPX_EXIT_CODE -ne 0 ]; then
        echo "Error: npx tsx command failed with exit code $NPX_EXIT_CODE"
        docker ps -a | grep $file_name | awk '{print $1}' | xargs docker stop
        go run main.go dockerrun -c hack/mcp-agent/output/  -m $file_name  --debug
        docker image rm docker.io/library/$file_name:latest # remove the image
        FAIL_LIST_RUN+=($server)
        continue
    fi
    docker ps -a | grep $file_name | awk '{print $1}' | xargs docker stop
    docker image rm docker.io/library/$file_name:latest # remove the image
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to remove docker image for $server"
    fi
done

if [ ${#FAIL_LIST_BUILD[@]} -gt 0 ]; then
    echo "Failed to build the following servers: ${FAIL_LIST_BUILD[@]}"
    echo "Total number of failed servers: ${#FAIL_LIST_BUILD[@]}"
fi

if [ ${#FAIL_LIST_RUN[@]} -gt 0 ]; then
    echo "Failed to run the following servers: ${FAIL_LIST_RUN[@]}"
    echo "Total number of failed servers: ${#FAIL_LIST_RUN[@]}"
fi
if [ ${#FAIL_LIST_BUILD[@]} -gt 0 ] || [ ${#FAIL_LIST_RUN[@]} -gt 0 ]; then
    exit 1
fi

echo "All servers tested successfully."
exit 0
