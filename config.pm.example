# System configuration	[all site-wide]
use constant ADMIN_PASSWORD => 'CHANGEME';				# Administrator password
use constant ADMIN_COUNTER  => 'CHANGEME';				# Administrator countersign	
use constant SECRET_KEY     => 'CHANGEME';				# Cryptographic secret
use constant FLOOD_DELAY    => '60';					# Same-IP delay between posts for all boards
use constant ADMIN_RECENT   => '20';					# Number of posts listed in admin script
use constant SITE_URL		=> 'textboard.dynu.com';	# Url of site to filter to → for internal linking
use constant BOARDS         => (						# Board directories and titles ([a-z0-9]+)
                                 'board'  => 'Bulletin Board'
                               , 'lounge' => 'Cool BBS'
                               );

# Board configuration
use constant DEFAULT_NAME	=> 'Anonymous';		# Default name if none is entered
use constant TIME_SETTINGS  => 'STANDARD';		# Timestamp display (STANDARD, READABLE, DQN, SAGERU) 
use constant TRIP_KEY       => '!';				# Key in front of tripcodes
use constant FORCE_ANON		=> '0';				# Force posters to be anonymous? (0 = no, 1 = yes)
use constant POST_TRUNCATE  => '5';				# Lines to truncate posts at (0 = disable)
use constant SHOW_SAGE      => '1';				# Make sage visible on user's name? (0 = no, 1 = yes)
use constant NO_MALFORMED   => '1';				# Stop malformed and unparsed markup? (0 = no, 1 = yes)
use constant TIME_ZONE      => '0';				# Time zone of the board in + or - hours. (0 = GMT)
use constant REDIRECT_DELAY => '2';			    # Redirect delay after posting
use constant CAPPED_TRIPS   => (				# Capped Tripcodes, may contain valid HTML5	[site-wide]
                                 '!example1' => 'capped'
                               , '!example2' => '<b style="color:purple">ADMIN</b>'
                               );
							   

# Anti-necromancy configuration
use constant THREAD_NECROMANCY => '0';  # How to deal with old thread necromancy?
                                        # (0 = disabled,
                                        #  1 = allow posting, but do not bump,
                                        #  2 = do not allow posting)
use constant NECROMANCY_DAYS   => '90'; # How many days old is a thread considered dead?
use constant NECROMANCY_AGE    => '2';  # Count a thread's age from which post?
                                        # (0 = from the first post,
                                        #  1 = since last bumped,
                                        #  2 = from the most recent post)
# Post limitations
use constant POST_LIMIT     => '1000';  # Max post limit per thread
use constant COMMENT_LENGTH => '32000'; # Max comment length
use constant SUBJECT_LENGTH => '80';    # Max subject length
use constant NAME_LENGTH    => '600';   # Max name length (does not include tripcode portion)

# Page display
use constant PAGE_CSS        => 'style.css';      # Stylesheet filename	[site-wide]
use constant ALT_CSS         => '0';              # Alternative stylesheets (0 = disabled)
use constant PAGE_POSTS      => '5';              # Posts shown in preview excluding the first post
use constant PAGE_THREADS    => '10';             # Threads shown on front page
use constant PAGE_THREADLIST => '40';             # Thread links on threadlist
use constant PRETTIFY_CODE	 => '0';			  # Syntax highlighting in codeblocks? (0 = no, 1 = yes)

#----------------------------------------------------------------------------------------------------

use constant FORCE_ANON_LOUNGE		=> '1';

1;
