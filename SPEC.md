# ped-tv spec

PED TV is a website for hosting videos to display on the waiting room screens in paediatric A&E departments in England.

It hosts multiple playlists, composed of videos and images uploaded by NHS staff. Whilst anyone can visit the website and play the content, only named staff can upload.

There is a public facing part of the site where you can see the playlists, play them and browse the individual media within them. There is also a private management area where content is uploaded.

The management area includes a playlist editor where:

- New playlists can be created
- Existing playlists can be edited
- Set a single playlist as the "default"
- Archive old playlists so they are only visible to admins

Draft playlist should be hidden from the public site entirely.

The playlist editor allows admins to upload videos and images. Both can then be dragged and dropped into the playlist. Images are given a duration that they are displayed for whereas videos are played in full.

Content (both videos and images) have an associated "provider" who created the media originally. Each provider has a logo, description and a link to their site. For example the Lullaby Trust provide content on safe sleeping for babies. Logo and description are optional.

Uploaded content should have thumnbails to easily identify which content is which.

When a playlist is saved it is "pressed" into two video files:

- A single mp4 that can be downloaded from the playlist page
- An HLS streaming playlist

It should also save a thumbnail for the whole video.

When a user visits a playlist page they can play the HLS video. By default it should loop infinitely. Most users will full screen this to put on the waiting room screen.

Managers can set a playlist as the "main" playlist that appears on the front page.

Media cannot be deleted if referenced by any existing playlist.

## Authentication

Django users. No public sign up, admins will create them all.


## Media

The pressed video should be 1280x720 @ 25fps (720p25, PAL friendly) for maximum compatibility.


## Pages

### Common furniture

A header with the PED TV logo in the top left hand side and a "Sign In" link on the top right hand side.

Once logged in the right hand side has an "Manage" link that goes to the management page and a "Log Out" link.

### Front page

The HLS video for the main playlist in a hero container with a "Play" button. When Play is clicked the video goes
full screen and automatically loops.

Below is a prominent link to download the MP4 pressed version of the playlist.

Underneath the hero is a list of publically visible playlists with the main playlist first. Each list item is a link
to the playlist page.

### Playlist page

Hero container for playing the playlist as per the front page. Below is the list of media in the playlist with the metadata
for each provider next to it. Option to download MP4 pressed version.

### Management homepage (logged in)

List of playlists with the main playlist shown first and marked appropriately. Can edit an existing playlist or create a new one.

Show status of each playlist (i.e. is a "press" in progress).

### Provider management page

CRUD for providers (including metadata as described above).

### Playlist management page

- Add a new video or image (set duration for image)
  - Support drag drop file from outside of browser
- Associate the uploaded media with a provider
- Drag drop to rearrange media
- Button to "Publish" i.e. press the playlist, trigger creation of HLS video and MP4 version, make it publically visible.
- Show status of each playlist (i.e. is a press in progress)
- Button to set playlist as main playlist (if playlist press is complete).
- Button to archive a playlist so it's not publically visible any more.


## Tech stack

Local development should be wrapped up in Docker with an associated docker-compose file.

Helper scripts to manage (e.g. `s/up` script to start up the local dev instance).

- Python (with uv for library manegement)
- Django
  - Postgres
- HTMX where needed (no JS UI libraries)
- django-tasks for background tasks
  - ffmpeg for video management
- NHS UK design system (https://service-manual.nhs.uk/design-system)
  - CSS only, no Nunjucks
- Object storage for media upload
  - Garage in local dev
- hls.js for video playback
