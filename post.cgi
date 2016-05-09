#!/usr/bin/perl -Tw

use strict;
use CGI::Carp 'fatalsToBrowser';
use Fcntl ':flock';
use File::ReadBackwards;
use lib '.';

BEGIN {
    require "config.pm";
    require "common.pm";
    require "html.pm";
    require "markup.pm";
}

abort('This software is using the default cryptographic secret key')
  if SECRET_KEY eq 'CHANGEME';

# collect data
my %form    = form_data();
my $board   = $form{'board'};
my $thread  = $form{'thread'};
my $subject = $form{'subject'};
my $comment = $form{'message'};
my $name    = $form{'name'};
my $sage    = $form{'sage'};
my $noko    = $form{'noko'};
my $spam    = $form{'comment'};
my $ip      = $ENV{'REMOTE_ADDR'}; # HTTP_CF_CONNECTING_IP , REMOTE_ADDR
my $dir     = $ENV{'SCRIPT_NAME'};
my $time    = time;

my $preview	  = 1 if ($form{'reply'} eq 'Preview');
my $postcount = 1;
my $permasage = 0;
my $closed    = 0;

# sanitize data
($board )  = $board   =~ /^([a-z0-9]+)$/;
($thread)  = $thread  =~ /^([0-9]+)$/;
($subject) = $subject =~ /^([^\n]+)$/;
($name)    = $name    =~ /^([^\n]+)$/;
($sage)    = $sage    =~ /^on$/;
($noko)    = $noko    =~ /^on$/;
($ip)      = $ip      =~ /^([0-9a-fA-F:\.]+)$/;
($dir)     = $dir     =~ /^(.*)\/[^\/]*$/;

# verify data
abort('Spam!') if length $spam > 0;
abort('Tainted!') if (length $subject > 0) && (length $thread > 0) || (length $subject > 0) && $sage || !$ip;
abort('Thread does not exist') if (length $thread > 0) && !-e "$board/res/$thread.html";
if ($ENV{'REQUEST_METHOD'} eq 'POST') {
    abort('Board not defined') if (length $board == 0);
    my %boards = BOARDS;
    my $listed;
    while (my ($key, $value) = each(%boards)) {
        $listed = 1 if $board eq $key;
    }
    abort('Board is not active') unless $listed;
    abort('No subject') if (length $subject == 0) && (length $thread == 0);
    abort('No comment') if length $comment == 0;
}
my $trip;
if (length $name > 0 and !board_settings("FORCE_ANON", $board)){
($name, $trip) = tripcode($name);
}else{
$name = board_settings("DEFAULT_NAME", $board);
my $trip = 0;};
$name = eval{decode('utf8', $name)} || $name; #accept SJIS

abort('Flood detected')   if -e "$board/res/$time.html" && length $subject > 0;
abort('Post less often')  if ($time - read_log($ip, $time)) <= FLOOD_DELAY;
abort('Subject too long') if length $subject > board_settings("SUBJECT_LENGTH", $board);
abort('Comment too long') if length $comment > board_settings("COMMENT_LENGTH", $board);
abort('Name too long')    if length $name    > board_settings("NAME_LENGTH", $board);
abort('Subject contains a blacklisted item') if blacklist($subject, 'spam.txt');
abort('Comment contains a blacklisted item') if blacklist($comment, 'spam.txt');
abort('Name contains a blacklisted item')    if blacklist($name,    'spam.txt');
abort('Your IP address is blacklisted')      if blacklist($ip,      'ban.txt');

my $newthread = 1 unless $thread;
my ($last_bumped, $last_posted);
if ($thread) {
    ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject) = read_thread_info($board, $thread);
    $postcount++;
    abort('Post limit reached') if $postcount > board_settings("POST_LIMIT", $board);
    abort('Thread is closed')   if $closed;
    abort('Malformed thread.') unless ($last_bumped && $last_posted);
    if (board_settings("THREAD_NECROMANCY", $board)) {
        my $limit = board_settings("NECROMANCY_DAYS", $board) * 86400;
        my $diff;
        if (board_settings("NECROMANCY_AGE", $board) == 0) {
            $diff = $time - $thread;
        }
        elsif (board_settings("NECROMANCY_AGE", $board) == 1) {
            $diff = $time - $last_bumped;
        }
        elsif (board_settings("NECROMANCY_AGE", $board) == 2) {
            $diff = $time - $last_posted;
        }
        if (board_settings("THREAD_NECROMANCY", $board) == 1) {
            $sage = 1 if $diff > $limit;
        }
        elsif (board_settings("THREAD_NECROMANCY", $board) == 2) {
            abort("This thread is too old, you can't reply anymore") if $diff > $limit;
        }
    }
}
else {
	if (board_settings("TIME_SETTINGS", $board) eq 'SAGERU'){ #random thread id for sageru
	my $rand = (int(rand(1000000000-10))+10);
	until (!-e "$board/res/$rand.html"){
	$rand = (int(rand(1000000000-10))+10);
	};
    ($thread, $last_bumped, $last_posted) = ($rand, $time, $time);
	}else{
	($thread, $last_bumped, $last_posted) = ($time, $time, $time);
	}
}
$sage = $permasage || $sage ? 1 : 0;

my ($parsed_comment, $malformed) = markup($comment, $dir, $board, $thread);
abort('Comment contains malformed markup') if ($malformed && board_settings("NO_MALFORMED", $board)) && !$preview;

# process data
if ($ENV{'REQUEST_METHOD'} eq 'POST') {
    if (!-d "$board/res/") { mkdir("$board/res", 0755) || die "Cannot create directory: $!"; }
    if ($preview) { print_preview($dir, $board, $name, $trip, $comment, $parsed_comment, $postcount, $sage, $subject, $newthread, $thread) }
    write_thread($dir, $board, $thread, $last_bumped, $last_posted, $closed, $permasage, $postcount, $subject, $name, $trip, $time, $sage, $parsed_comment);
    write_log($ip, $time, $board, $thread, $postcount, $sage);
    build_pages($dir, $board);
    redirect($dir, $board, $thread, $postcount, $sage, $noko);
}
else {
    my %boards = BOARDS;
    while (my ($key, $value) = each(%boards)) {
        if (!-d "$key/") { mkdir("$key", 0755) || die "Cannot create directory: $!"; }
        build_pages($dir, $key);
    }
    redirect($dir, 0, 0, 0, 0, 0);
}
