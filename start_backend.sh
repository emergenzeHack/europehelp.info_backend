docker build . --tag ukrainehelp_backend
docker stop ukrainehelp_backend; docker rm ukrainehelp_backend

docker run -d -p 5000:5000 --name "ukrainehelp_backend" -v /root/docker/nginx-proxy/certsHTTPS/:/certs:ro ukrainehelp_backend
