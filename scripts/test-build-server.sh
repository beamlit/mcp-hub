FILENAME=$1.yaml
IS_CHECKPOINT=false
FAIL_LIST=()

file_name=$(basename $FILENAME | sed 's/.yaml//g')
echo "Building $file_name"
go run main.go import -c hack/mcp-agent/output/  -m $file_name  --debug
if [ $? -ne 0 ]; then
    echo "Failed to build $file_name"
    FAIL_LIST+=($file_name)
fi
docker image rm docker.io/library/$file_name:latest # remove the image


if [ ${#FAIL_LIST[@]} -gt 0 ]; then
    echo "Failed to build the following servers: ${FAIL_LIST[@]}"
    echo "Total number of failed servers: ${#FAIL_LIST[@]}"
    exit 1
fi
