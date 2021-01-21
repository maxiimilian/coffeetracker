# Preparations
- Rename `splitwise.example.ini` and `users.example.ini` to `splitwise.ini` and `users.ini`.
- Add desired number of users to `users.ini`.
- Don't manually change `splitwise.ini`. Access codes will be stored here automatically after login.

# Setup
- Build app container with `docker-compose build`. **Note**: This has to be repeated each time `/app` changes, i.e. is updated.
- Start container with `docker-compose up`.
- App is available (by default) on port 8080 of host. Change this in `docker-compose.yml` if required.

# Regular Operation
- Start: `docker-compose start`
- To apply new settings, e.g. add new users, the app has to be restarted: `docker-compose restart`
- Stop: `docker-compose stop`
- **Important**: `./data` is mounted as volume inside the Docker container. It will contain all bills and settings. It should be backuped!
