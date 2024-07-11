container_name=your_container_name
image_path=your_image_path


docker run \
  -d \
  -p 9910:9910 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --gpus all \
  -v /usr/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu \
  --name $container_name \
  $image_path