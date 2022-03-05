docker build . --tag europehelp_backend
docker stop europehelp_backend; docker rm europehelp_backend

docker run -d -p 5000:5000 --name "europehelp_backend" europehelp_backend
