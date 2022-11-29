echo -e "\n### REMOVING DANGLING IMAGES ###\n"
docker rmi --force $(docker images -f "dangling=true" -q)
echo -e "\n### REMOVING EXITED CONTAINERS ###\n"
docker rm $(docker ps -a -f status=exited -f status=created -q)
echo -e "\n### BUILDING DOCKER CONTAINER ###\n"
docker-compose build --no-cache
echo -e "\n### RUN DOCKERIZED BOT ###\n"
docker-compose up --remove-orphans