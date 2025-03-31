CHECKPOINT="big-brain-mcp.yaml"
IS_CHECKPOINT=false
FAIL_LIST=()
for server in $(ls hack/mcp-agent/output); do
    if [ "$server" == "$CHECKPOINT" ]; then
        IS_CHECKPOINT=true
    fi

    if [ "$IS_CHECKPOINT" == "false" ]; then
        echo "Checkpoint $CHECKPOINT not found"
        exit 1  
    fi


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
        FAIL_LIST+=($server)
        continue
    fi
   
    npx tsx --tsconfig=web-search/tsconfig.json web-search/client.ts
    NPX_EXIT_CODE=$?
    if [ $NPX_EXIT_CODE -ne 0 ]; then
        echo "Error: npx tsx command failed with exit code $NPX_EXIT_CODE"
        docker ps -a | grep $file_name | awk '{print $1}' | xargs docker stop
        docker image rm docker.io/library/$file_name:latest # remove the image
        FAIL_LIST+=($server)
        continue
    fi
    docker ps -a | grep $file_name | awk '{print $1}' | xargs docker stop
    docker image rm docker.io/library/$file_name:latest # remove the image
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to remove docker image for $server"
    fi
done

if [ ${#FAIL_LIST[@]} -gt 0 ]; then
    echo "Failed to build the following servers: ${FAIL_LIST[@]}"
    echo "Total number of failed servers: ${#FAIL_LIST[@]}"
    exit 1
fi

echo "All servers tested successfully."
exit 0
