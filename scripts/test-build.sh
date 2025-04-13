CHECKPOINT=$1.yaml
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
    echo "Building $file_name"
    go run main.go import -c hack/mcp-agent/output/  -m $file_name  --debug
    if [ $? -ne 0 ]; then
        echo "Failed to build $file_name"
        FAIL_LIST+=($file_name)
    fi
    docker image rm docker.io/library/$file_name:latest # remove the image
done

if [ ${#FAIL_LIST[@]} -gt 0 ]; then
    echo "Failed to build the following servers: ${FAIL_LIST[@]}"
    echo "Total number of failed servers: ${#FAIL_LIST[@]}"
    exit 1
fi
