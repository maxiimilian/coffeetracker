.PHONY: initial update

DATE := $(shell date +%Y-%m-%d_%H-%M-%S)

update:
	# Make backup of data
	cp -n -r ./data ./data_bak_$(DATE)
	# Pull newest code
	git pull
	# Update docker container and restart it
	docker-compose build
	docker-compose up -d

initial:
	echo "Not yet implemented!"
