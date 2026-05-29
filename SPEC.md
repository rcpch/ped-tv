# ped-tv spec

PED TV is a website for hosting videos to display on the waiting room screens in paediatric A&E departments in England.

It hosts multiple playlists, composed of videos and images uploaded by NHS staff. Whilst anyone can visit the website and play the content, only named staff can upload.

There is a public facing part of the site where you can see the playlists, play them and browse the individual media within them. There is also a private admin area where content is uploaded.

The admin area includes a playlist editor where:

- New playlists can be created
- Existing playlists can be edited
- Set a single playlist as the "default"
- Archive old playlists so they are only visible to admins

The playlist editor allows admins to upload videos and images. Both can then be dragged and dropped into the playlist. Images are given a duration that they are displayed for whereas videos are played in full.

Content (both videos and images) have an associated "provider" who created the media originally. Each provider has a logo, description and a link to their site. For example the Lullaby Trust provide content on safe sleeping for babies.

Uploaded content should have thumnbails to easily identify which content is which.

When a playlist is saved it is "pressed" into two video files:

- A single mp4 that can be downloaded from the playlist page
- An HLS streaming playlist

It should also save a thumbnail for the whole video.

When a user visits a playlist page they can play the HLS video. By default it should loop infinitely. Most users will full screen this to put on the waiting room screen.

## Tech stack

- Python (with uv for library manegement)
- Django
  - sqlite
  - litestream for backup to S3 compatible storage
- HTMX
- django-tasks for background tasks
- NHS UK design system (https://service-manual.nhs.uk/design-system)
  - CSS only, no Nunjucks

Local development should be wrapped up in Docker with an associated docker-compose file.

Helper scripts to manage (e.g. `s/up` script to start up the local dev instance).