# Emanon BBS
http://textboard.dynu.com/

Emanon BBS is software for hosting an anonymous textboard. It is written on top of Tablecat BBS aiming to add responsive layouts and a more efficient browsing experience without losing its web 1.0 feel.
Features

### Features
- Mobile-responsive layout that properly scales text.
- Double-column isotope layout for wider desktop resolutions.
- Filter and sort threads with isotope.
- Site-wide thread index displaying recent posts.
- Simple image uploader with gallery.

##### Smaller changes
- Board-specific configurations in config.pm.
- Re-added BBcode.
- SJIS support for names and tripcodes.
- Kareha-styled subback page.
- Support for sageru-styled boards.
- Display time in Eternal September or a "M D, Y H:M" format.
- Automatic page reload after posting.
- Quick-Reply form hidden by default
- Board navigation bar

##### The Name
Emanon is an ananym of No Name, inspired by the lovely manga Omoide Emanon. It also used to be a name for the element argon, which ties in with the chemistry based name of isotope.

## How to install
1. Extract files to desired directory
2. Make desired changes to config.pm
3. CHMOD all files with the file type .cgi to 755
4. Run post.cgi 

##### Install image gallery

1. Place upload.cgi in desired board folder. (optional)
2. Make changes to settings in upload.cgi
3. Run upload.cgi 
