#!/usr/bin/perl -Tw

use strict;
use CGI 'form';
use CGI::Carp 'fatalsToBrowser';
use Fcntl ':flock';
use File::ReadBackwards;
use lib '.';

BEGIN {
    require "config.pm";
    require "common.pm";
    require "html.pm";
}

die 'Security Error: This software is using the default security settings'
  if ADMIN_PASSWORD eq 'CHANGEME'
  || ADMIN_COUNTER eq 'CHANGEME'
  || SECRET_KEY eq 'CHANGEME';

die 'Security Error: This software is using the same password and countersign'
  if ADMIN_PASSWORD eq ADMIN_COUNTER;

# collect data, panel entry
my $q = CGI->new;
my $passwd   = $q->param('passwd');
my $counter  = $q->param('counter');
my $remember = $q->param('remember');
my $cookie   = $ENV{'HTTP_COOKIE'};
my $dir      = $ENV{'SCRIPT_NAME'};
my $server   = $ENV{'SERVER_NAME'};

# sanitize data
($remember) = $remember =~ /^on$/;
($dir)      = $dir      =~ /^(.*)\/[^\/]*$/;

# process data
my $encode_passwd = encode_base64(RC4(SECRET_KEY, ADMIN_PASSWORD));
my $encode_counter = encode_base64(RC4(SECRET_KEY, ADMIN_COUNTER));

# verify cookies
my ($cookies_matched, $passwd_matched, $counter_matched);
my @cookies = split(/;/, $cookie);
for (@cookies) {
    chomp;
    my $item = $_;
    if ($item =~ /^\s?passwd=(.*)/) {
        my $cookie_passwd = $1;
        if ($cookie_passwd eq $encode_passwd) {
            $passwd_matched = 1;
        }
    }
    elsif ($item =~ /^\s?countersign=(.*)/) {
        my $cookie_counter = $1;
        if ($cookie_counter eq $encode_counter) {
            $counter_matched = 1;
        }
    }
}
if ($passwd_matched && $counter_matched) { $cookies_matched = 1; }

# print cookies
if ($passwd eq ADMIN_PASSWORD && $counter eq ADMIN_COUNTER) {
    print
      "Set-Cookie:passwd=$encode_passwd;"
    , $remember ? 'expires=Fri, 19-Jan-2038 03:14:07 GMT;' : ''
    , "path=/; domain=$server;HttpOnly\n"
    , "Set-Cookie:countersign=$encode_counter;"
    , $remember ? 'expires=Fri, 19-Jan-2038 03:14:07 GMT;' : ''
    , "path=/; domain=$server;HttpOnly\n"
    , "Status: 301 Go West\nLocation: $dir/admin.cgi\n\n"
    ;
    exit;
}

# print entry page
if (!$cookies_matched) {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;text-align:center;}'
    , 'h1{font-weight:normal;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1>Management Panel</h1>'
    , '<form action="' . $dir . '/admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , 'Password: '
    , '<input type="password" name="passwd" size="6"> '
    , '<input type="password" name="counter" size="6"> '
    , '<input type="submit" value="Login" name="submit">'
    , '<p><label><input type="checkbox" name="remember"> Remember this browser</label></p>'
    , '</form>'
    , '</body>'
    , '</html>'
    ;
    exit;
}

### ADMINISTRATIVE WORK ###
my $submit     = $q->param('input');
my $file       = $q->param('file');
my $content    = $q->param('content');
my @postlist   = $q->param('postlist');
my @threadlist = $q->param('threadlist');
my $board      = $q->param('board');
my $ip         = $q->param('ip');

($board) = $board =~ /([a-z0-9]+)/;
($file)  = $file  =~ /^([\w\.]+)$/;

if ($submit eq 'Rebuild all threads') {
    my %boards = BOARDS;
    while (my ($board, $value) = each(%boards)) {
        my @thread_list = read_thread_list($board);
        for (@thread_list) {
            /^([0-9]+) ([0-9]+) ([0-9]+) ([01]) ([01]) ([0-9]+) (.*)$/;
            my ($last_bumped, $last_posted, $thread, $closed, $permasage, $postcount, $subject) = ($1, $2, $3, $4, $5, $6, $7);
            write_thread($dir, $board, $thread, $last_bumped, $last_posted, $closed, $permasage, $postcount, $subject);
        }
        build_pages($dir, $board);
    }
	system("/bin/bash encode.sh");
    admin_redirect();
}
elsif ($submit eq 'Rebuild index') {
    rebuild_index();
    admin_redirect();
}
elsif ($submit eq 'Delete log file') {
    delete_log();
    admin_redirect();
}
elsif ($submit eq 'Save changes') {
    save_file($file, $content);
    admin_redirect('edit='.$file);
}
elsif ($submit eq 'Delete selected posts') {
    my %selectposts = ();
    my $redir = 'board='.$board if $board;
    for my $line (@postlist) {
        my ($board, $thread, $postnum) = split(',', $line);
        push(@{$selectposts{"$board,$thread"}}, $postnum);
    }
    foreach my $group (keys %selectposts) {
        my ($board, $thread) = split(',', $group);
        delete_posts($board, $thread, @{$selectposts{$group}});
        delete_log_entries($board, $thread, @{$selectposts{$group}});
    }
    rebuild_index();
    admin_redirect($redir);
}
elsif ($submit eq 'Delete all') {
    delete_all($ip);
    rebuild_index();
    admin_redirect();
}
elsif ($submit eq 'Blacklist this IP address') {
    blacklist_ip($ip);
    admin_redirect('ip='.$ip);
}
elsif ($submit eq 'Delete') {
    for my $thread (@threadlist) {
        ($thread) = $thread =~ /([0-9]+)/;
        delete_thread($board, $thread);
    }
    build_pages($dir, $board);
    admin_redirect('board='.$board);
}
elsif ($submit eq 'Close') {
    for my $thread (@threadlist) {
        ($thread) = $thread =~ /([0-9]+)/;
        my ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject) = read_thread_info($board, $thread);
        next if $closed == 1;
        write_thread($dir, $board, $thread, $last_bumped, $last_posted, 1, $permasage, $postcount, $subject);
    }
    build_pages($dir, $board);
    admin_redirect('board='.$board);
}
elsif ($submit eq 'Open') {
    for my $thread (@threadlist) {
        ($thread) = $thread =~ /([0-9]+)/;
        my ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject) = read_thread_info($board, $thread);
        next if $closed == 0;
        write_thread($dir, $board, $thread, $last_bumped, $last_posted, 0, $permasage, $postcount, $subject);
    }
    build_pages($dir, $board);
    admin_redirect('board='.$board);
}
elsif ($submit eq 'Permasage') {
    for my $thread (@threadlist) {
        ($thread) = $thread =~ /([0-9]+)/;
        my ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject) = read_thread_info($board, $thread);
        next if $permasage == 1;
        write_thread($dir, $board, $thread, $last_bumped, $last_posted, $closed, 1, $postcount, $subject);
    }
    build_pages($dir, $board);
    admin_redirect('board='.$board);
}
elsif ($submit eq 'Un-Permasage') {
    for my $thread (@threadlist) {
        ($thread) = $thread =~ /([0-9]+)/;
        my ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject) = read_thread_info($board, $thread);
        next if $permasage == 0;
        write_thread($dir, $board, $thread, $last_bumped, $last_posted, $closed, 0, $postcount, $subject);
    }
    build_pages($dir, $board);
    admin_redirect('board='.$board);
}

### MANAGEMENT PANEL ###

# collect data, management panel
my $thread = $q->param('thread');
my $edit   = $q->param('edit');
my $action = $q->param('action');


# print rebuild all threads page
if ($action eq 'delete_ip') {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{color:#000;padding:4px;}'
    , 'form{display:inline}'
    , '.posts{width:40px;display:inline-block;}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , "<h2>Delete all threads and posts originating from $ip?</h2>"
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<input type="submit" value="Delete all" name="submit">'
    , '&emsp;<input type="button" value="Cancel" onClick="history.go(-1);return true;">'
    , '<input type="hidden" value="Delete all" name="input">'
    , '<input type="hidden" value="'.$ip.'" name="ip">'
    , '</form>'
    , '</body>'
    , '</html>'
    ;
}
elsif ($action eq 'rebuildall') {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{background:#8080C0;color:#FFF;padding:4px;}'
    , 'form{display:inline}'
    , '.box{background:#FAFAFA;border:1px solid #aaa;padding:4px;}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , "<h2>Rebuild index</h2>"
    , '<div class="box">'
    , "Rebuilds all the threads of all boards."
    , '</div><br>'
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<input type="submit" value="Rebuild all threads" name="submit">'
    , '<input type="hidden" value="Rebuild all threads" name="input">'
    , '</form>'
    , '</body>'
    , '</html>'
    ;
}
# print rebuild index page
elsif ($action eq 'rebuild') {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{background:#8080C0;color:#FFF;padding:4px;}'
    , 'form{display:inline}'
    , '.box{background:#FAFAFA;border:1px solid #aaa;padding:4px;}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , "<h2>Rebuild index</h2>"
    , '<div class="box">'
    , "Rebuilds the index page and subback page of all boards."
    , '</div><br>'
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<input type="submit" value="Rebuild index" name="submit">'
    , '<input type="hidden" value="Rebuild index" name="input">'
    , '</form>'
    , '</body>'
    , '</html>'
    ;
}
# print log delete page
elsif ($action eq 'logdel') {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{background:#8080C0;color:#FFF;padding:4px;}'
    , 'form{display:inline}'
    , '.box{background:#FAFAFA;border:1px solid #aaa;padding:4px;}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , "<h2>Delete log file</h2>"
    , '<div class="box">'
    , "Deletes the log file. Note: It is safe to delete the log file, it will re-create on the next posting."
    , '</div><br>'
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<input type="submit" value="Delete log file" name="submit">'
    , '<input type="hidden" value="Delete log file" name="input">'
    , '</form>'
    , '</body>'
    , '</html>'
    ;
}
# print recent posts page
elsif ($action eq 'logview') {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{background:#8080C0;color:#FFF;padding:4px;}'
    , 'form{display:inline}'
    , '.shell{border:1px solid #8080C0;background:#FFF;margin-bottom:2px;}'
    , '.shell-body{padding:0 4px 4px;display:block;}'
    , '.highlight:hover{background:#DCDCED;display:block;}'
    , '.box{background:#FAFAFA;border:1px solid #aaa;padding:4px;}'
    , '.posts{width:40px;display:inline-block;}'
    , '.red{background:#4C516D;color:white;display:inline-block;text-align:center;width:104px}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , '<h2>Viewing ' . ADMIN_RECENT . ' most recent posts</h2>'
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<div class="box">'
    , '<strong>Recent Posts Options</strong><br>'
    , '<input type="submit" value="Delete selected posts" name="submit">'
    , '<input type="hidden" value="Delete selected posts" name="input">'
    , '</div><br>'
    ;
    my $i = 0;
  if (-e 'log.txt') {
	  my $read = File::ReadBackwards->new('log.txt');
    while( defined( my $line = $read->readline ) ) {
        my ($log_ip, $board, $thread, $postnum, $sage) = $line =~ /^(.*?) (?:[0-9]+) (.*?) ([0-9]+) ([0-9]+) ([0-1])/;
        my $ip = RC4(SECRET_KEY, decode_base64($log_ip));
        open my $read, '<:utf8', "$board/res/$thread.html" || die "Cannot read thread file: $!";
        flock $read, LOCK_SH;
        while (my $line = <$read>) {
            my ($l_postnum) = $line =~ /^<div class=\"post\" id=\"([0-9]+)\">/;
            my ($l_name)    = $line =~ /<span class=\"name(?:.*?)\">(.*?)<\/span>/;
            my ($l_trip)    = $line =~ /<span class=\"trip\">(.*?)<\/span>/;
            my ($l_comment) = $line =~ /<div class=\"comment\">(.*?)<\/div>/;
            #$l_name = encode('utf8', $l_name);
            $l_comment = encode('utf8', $l_comment);
            if ($l_postnum == $postnum) {
                print
                  "Admin: <a href=\"admin.cgi?board=$board&thread=$thread\"><strong>$board/$thread</strong></a> "
                , "<a href=\"admin.cgi?ip=$ip\"><span class=\"red\">$ip</span></a>"
                , '<div class="shell">'
                , '<label>'
                , '<span class="highlight">'
                , '<span class="shell-body">'
                , '<input type="checkbox" name="postlist" value="' . $board . ',' . $thread . ',' . $postnum . '"> '
                , "<strong>$l_postnum</strong> Name: <strong>$l_name</strong> $l_trip<br><span class=\"shell-body\">$l_comment</span>"
                , '</span></span></label>'
                , '</div><br>'
                ;
                $i++;
                last;
            }
        }
        close $read;
        last if $i == ADMIN_RECENT;
    }
  }
    print
      '</form>'
    , '</body>'
    , '</html>'
    ;
}
# print file edit page
elsif ($edit) {
    open my $read, '<', "$edit";
    my $content = do { local $/; <$read> };
    close $read;

    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{background:#8080C0;color:#FFF;padding:4px;}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '.box{background:#FAFAFA;border:1px solid #aaa;padding:4px;}'
    , 'code{background:#f0f0e0;color:purple;padding:2px;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , "<h2>Edit: $edit</h2>"
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<div class="box">'
    , '<strong>File Edit Options</strong><br>'
    , '<input type="submit" value="Save changes" name="submit">'
    , '<input type="hidden" value="Save changes" name="input">'
    , '<input type="hidden" value="',$edit,'" name="file">'
    , '</div><br>'
    , '<div class="box">'
    , 'Note: Each line is processed as a regular expression. Special characters must be escaped with a backslash to use them as literal characters.'
    , '</div><br>'
    , '<textarea rows="16" style="width:100%" name="content">' . html_escape($content) . '</textarea>'
    , '</form>'
    , '</body>'
    , '</html>'
    ;
}
# print user posts-list page
elsif ($ip) {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{background:#8080C0;color:#FFF;padding:4px;}'
    , 'form{display:inline}'
    , '.shell{border:1px solid #8080C0;background:#FFF;margin-bottom:2px;}'
    , '.shell-body{padding:0 4px 4px;display:block;}'
    , '.highlight:hover{background:#DCDCED;display:block;}'
    , '.box{background:#FAFAFA;border:1px solid #aaa;padding:4px;}'
    , '.posts{width:40px;display:inline-block;}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , "<h2>Viewing IP Address: $ip</h2>"
    , '<div class="box">'
    , '<form action="admin.cgi" method="get" style="display:inline-block;background:red" onsubmit="this.submit.disabled=true">'
    , '<input type="submit" value="Delete all threads and posts originating from this IP address" style="width:400px;margin:3px;" name="submit">'
    , '<input type="hidden" name="action" value="delete_ip">'
    , '<input type="hidden" name="ip" value="' . $ip . '">'
    , '</form>&emsp;'
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<input type="submit" value="Blacklist this IP address" name="submit">'
    , '<input type="hidden" value="Blacklist this IP address" name="input">'
    , '<input type="hidden" name="ip" value="' . $ip . '">'
    , '</form>&emsp;'
    , blacklist($ip, 'ban.txt') ? '<strong>Blacklisted</strong>' : '<strong>Not blacklisted</strong>'
    , '</div>'
    , '<br>'
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<div class="box">'
    , '<strong>User Posts Options</strong><br>'
    , '<input type="submit" value="Delete selected posts" name="submit">'
    , '<input type="hidden" value="Delete selected posts" name="input">'
    , '</div>'
    ;
    my %userposts = ();
    open my $read, '<:utf8', 'log.txt' || die "Cannot read log file: $!";
    flock $read, LOCK_SH;
    while (<$read>) {
        chomp;
        /^([^\s]+) [0-9]+ ([^\s]+) ([0-9]+) ([0-9]+) ([0-1])$/;
        my ($log_ip, $log_board, $log_thread, $log_postnum, $log_sage) = ($1, $2, $3, $4, $5);
        if ( RC4(SECRET_KEY, decode_base64($log_ip)) eq $ip ) {
            push(@{$userposts{"$log_board,$log_thread"}}, $log_postnum);
        }
    }
    close $read;
    foreach my $group (keys %userposts) {
        my ($board, $thread) = split(',', $group);
        if (-e "$board/res/$thread.html") {
            print "<p>Thread: <a href=\"$dir/read.cgi/$board/$thread\"><strong>$board/$thread</strong></a></p>";
            open my $read, '<:utf8', "$board/res/$thread.html" || die "Cannot read thread file: $!";
            flock $read, LOCK_SH;
            while (my $line = <$read>) {
                my ($l_postnum) = $line =~ /^<div class=\"post\" id=\"([0-9]+)\">/;
                my ($l_name)    = $line =~ /<span class=\"name(?:.*?)\">(.*?)<\/span>/;
                my ($l_trip)    = $line =~ /<span class=\"trip\">(.*?)<\/span>/;
                my ($l_comment) = $line =~ /<div class=\"comment\">(.*?)<\/div>/;
                $l_name = encode('utf8', $l_name);
                $l_comment = encode('utf8', $l_comment);
                for my $postnum (@{$userposts{$group}}) {
                    if ($l_postnum == $postnum) {
                        print
                          '<div class="shell">'
                        , '<label>'
                        , '<span class="highlight">'
                        , '<span class="shell-body">'
                        , '<input type="checkbox" name="postlist" value="' . $board . ',' . $thread . ',' . $l_postnum . '"> '
                        , "<strong>$l_postnum</strong> Name: <strong>$l_name</strong> $l_trip<br><span class=\"shell-body\">$l_comment</span>"
                        , '</span></span></label>'
                        , '</div>'
                        ;
                        last;
                    }
                }
            }
            close $read;
        }
    }
    print
      '</form>'
    , '</body>'
    , '</html>'
    ;
}
# print thread posts-list page
elsif ($thread) {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{background:#8080C0;color:#FFF;padding:4px;}'
    , '.shell{border:1px solid #8080C0;background:#FFF;padding:0;}'
    , '.shell-body{padding:0 4px;display:block;whitespace:pre}'
    , '.highlight:hover{background:#DCDCED;display:block;}'
    , '.red{background:#4C516D;color:white;display:inline-block;text-align:center;width:104px}'
    , '.box{background:#FAFAFA;border:1px solid #aaa;padding:4px;}'
    , '.postnum{width:30px;display:inline-block;text-align:right}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , "<h2>Viewing thread: $board/$thread</h2>"
    , '<form action="admin.cgi" method="post" onsubmit="this.submit.disabled=true">'
    , '<div class="box">'
    , '<strong>Thread Options</strong><br>'
    , '<input type="submit" value="Delete selected posts" name="submit">'
    , '<input type="hidden" value="Delete selected posts" name="input">'
    , '<input type="hidden" value="'.$board.'" name="board">'
    , '</div>'
    , "<p>Thread: <a href=\"$dir/read.cgi/$board/$thread\"><strong>$board/$thread</strong></a></p>"
    , '<div class="shell">'
    ;
    open my $read, '<:utf8', "$board/res/$thread.html" || die "Cannot read thread file: $!";
    flock $read, LOCK_SH;
    while (my $line = <$read>) {
        chomp $line;
        my ($l_postnum) = $line =~ /^<div class=\"post\" id=\"([0-9]+)\">/;
        my ($l_name)    = $line =~ /<span class=\"name(?:.*?)\">(.*?)<\/span>/;
        my ($l_trip)    = $line =~ /<span class=\"trip\">(.*?)<\/span>/;
        my ($l_comment) = $line =~ /<div class=\"comment\">(.*?)<\/div>/;
        $l_name = encode('utf8', $l_name);
        $l_comment = encode('utf8', $l_comment);
        my $l_ip = get_ip($board, $thread, $l_postnum);
        $l_comment =~ s/[\s]+(<br>|<p>)/$1/g;
        $l_comment =~ s/[\s]{2,}//g;
        $l_comment =~ s/(?:<br>|<\/?p>)/ /g;
        $l_comment =~ s/<.*?>//g;
        #trimming
        $l_comment =~ s/&amp;/&/g;  #
        $l_comment =~ s/&lt;/</g;   #
        $l_comment =~ s/&gt;/>/g;   #
        $l_comment =~ s/&quot;/\"/g;#
        $l_comment =~ s/^(.{140}).*$/$1/;
        $l_comment =~ s/&/&amp;/g;  #
        $l_comment =~ s/</&lt;/g;   #
        $l_comment =~ s/>/&gt;/g;   #
        $l_comment =~ s/\"/&quot;/g;#
        next unless length $l_comment > 0;
        print
          '<label>'
        , '<span class="highlight">'
        , '<span class="shell-body">'
        , '<input type="checkbox" name="postlist" value="' . $board . ',' . $thread . ',' . $l_postnum . '"> '
        , "<span class=\"postnum\">$l_postnum</span> "
        , $l_ip ? "<a href=\"admin.cgi?ip=$l_ip\">" : ''
        , "<span class=\"red\">$l_ip</span>"
        , $l_ip ? "</a>" : ''
        , " <b>$l_name $l_trip</b> $l_comment"
        , '</span>'
        , '</span>'
        , '</label>'
        ;
    }
    close $read;
    print
      '</div>'
    , '</form>'
    , '</body>'
    , '</html>'
    ;
}
# print board threads-list page
elsif ($board) {
    my @thread_list = read_thread_list($board);
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'h1 a{color:inherit;text-decoration:inherit}'
    , 'h2{background:#8080C0;color:#FFF;padding:4px;}'
    , '.shell{border:1px solid #8080C0;background:#FFF;margin-bottom:2px;}'
    , '.shell-body{padding:0 4px;display:block;}'
    , '.highlight:hover{background:#DCDCED;display:block;}'
    , '.box{background:#FAFAFA;border:1px solid #aaa;padding:4px;}'
    , '.posts{width:40px;display:inline-block;}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1><a href="admin.cgi">Management Panel</a></h1>'
    , "<h2>Viewing board: $board</h2>"
    , '<form action="admin.cgi" method="post">'
    , '<div class="box">'
    , '<strong>Board Options</strong><br>'
    , '<input type="submit" value="Delete" name="input">&emsp;'
    , '[ <input type="submit" value="Close" name="input"> '
    , '<input type="submit" value="Open" name="input"> ]&emsp;'
    , '[ <input type="submit" value="Permasage" name="input"> '
    , '<input type="submit" value="Un-Permasage" name="input"> ]'
    , '</div>'
    , '<input type="hidden" value="'.$board.'" name="board"> '
    , '<br>'
    ;
    for (@thread_list) {
        /^([0-9]+) ([0-9]+) ([0-9]+) ([01]) ([01]) ([0-9]+) (.*)$/;
        my ($last_bumped, $last_posted, $thread, $closed, $permasage, $postcount, $subject) = ($1, $2, $3, $4, $5, $6, $7);
        $subject = encode('utf8', $subject);
        print
          '<div class="shell">'
        , '<label>'
        , '<span class="highlight">'
        , '<span class="shell-body">'
        , '<input type="checkbox" name="threadlist" value="' . $thread . '">&emsp;'
        , '<a href="admin.cgi?board=' . $board . '&amp;thread=' . $thread . '">View this thread</a>&emsp;'
        , 'Closed: ' . $closed
        , '&emsp;'
        , 'Permasage: ' . $permasage
        , '&emsp;'
        , 'Posts: <span class="posts">' . $postcount . '</span>'
        , "<strong>$subject</strong>"
        , '</span>'
        , '</span>'
        , '</label>'
        , '</div>'
        ;
    }
    print
      '</form>'
    , '</body>'
    , '</html>'
    ;
}
# print panel front page
else {
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="en">'
    , '<head>'
    , '<meta charset="UTF-8">'
    , '<title>Management Panel</title>'
    , '<style type="text/css">'
    , 'body{background:#F0F0F0;color:#000;font-family:Arial,sans-serif;font-size:10pt;}'
    , 'h1{font-weight:normal;}'
    , 'a{color:#222;}'
    , 'a:hover{color:#F00;}'
    , '</style>'
    , '</head>'
    , '<body>'
    , '<h1>Management Panel</h1>'
    , '<p><strong>Select a board:</strong></p>'
    ;
    my %boards = BOARDS;
    while (my ($key, $value) = each(%boards)) {
        print "<a href=\"admin.cgi?board=$key\">/$key/ - $value</a><br>";
    }
    print
      '<p><strong>Edit global files:</strong></p>'
    , '<a href="admin.cgi?edit=spam.txt">./spam.txt</a><br>'
    , '<a href="admin.cgi?edit=ban.txt">./ban.txt</a><br>'
    , '<p><strong>Other actions:</strong></p>'
    , '<a href="admin.cgi?action=logview">View recent posts</a><br>'
    , '<a href="admin.cgi?action=logdel">Delete log file</a><br>'
    , '<a href="admin.cgi?action=rebuild">Rebuild index</a><br>'
    , '<a href="admin.cgi?action=rebuildall">Rebuild all threads</a><br>'
    , '</body>'
    , '</html>'
    ;
}

# special subroutines

sub get_ip($$$) {
    my ($board, $thread, $postnum) = @_;
    my $ip;
    open my $read, '<:utf8', 'log.txt' || die "Cannot read log file: $!";
    flock $read, LOCK_SH;
    while (<$read>) {
        chomp;
        #$ip $time $board $thread $postcount
        /^([^\s]+) [0-9]+ ([^\s]+) ([0-9]+) ([0-9]+) ([0-1])$/;
        my ($log_ip, $log_board, $log_thread, $log_postnum, $sage) = ($1, $2, $3, $4, $5);
        if ("$board $thread $postnum" eq "$log_board $log_thread $log_postnum") {
            $ip = RC4(SECRET_KEY, decode_base64($log_ip));
        }
    }
    return $ip;
}

sub html_escape($) { # for html presentation
    my $str = shift;
    $str =~ s/&/&amp;/g;
    $str =~ s/</&lt;/g;
    $str =~ s/>/&gt;/g;
    $str =~ s/\"/&quot;/g;
    return $str;
}

sub admin_redirect($) {
    my $relink = shift;
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html><head>'
    , '<title>Action complete!</title>'
    , '<meta http-equiv="refresh" content="3;'
    , ' url=admin.cgi?' . $relink . '">'
    , '</head><body>Action complete!</body></html>'
    ;
    exit;
}

# admin work subroutines

sub rebuild_index {
    my %boards = BOARDS;
    while (my ($board, $value) = each(%boards)) {
        build_pages($dir, $board);
		system("/bin/bash encode.sh $board/index.html ");
    }
}

sub delete_log {
    return unless -e "log.txt";
    unlink("log.txt") or die "Cannot delete log file: $!";
}

sub save_file {
    my ($file, $content) = @_;
    $content =~ s/&amp;/&/g;
    $content =~ s/&lt;/</g;
    $content =~ s/&gt;/>/g;
    $content =~ s/&quot;/\"/g;
    open my $fh, '>', $file || die "Cannot write file: $!";
    flock $fh, LOCK_EX;
    print $fh "$content";
    close $fh;
}

sub delete_posts {
    my ($board, $thread, @posts) = @_;
    @posts = sort { $a <=> $b } @posts;
    if (@posts[0] == 1) {
        delete_thread($board, $thread);
        return;
    }
    elsif (!-e "$board/res/$thread.html") { return }
    open my $temp, '>:utf8', "$board/$thread.tmp" || die "Cannot write temporary file: $!";
    flock $temp, LOCK_EX;
    open my $read, '<:utf8', "$board/res/$thread.html" || die "Cannot read thread file: $!";
    flock $read, LOCK_SH;
    while (my $line = <$read>) {
        chomp $line;
        my ($l_postnum) = $line =~ /^<div class=\"post\" id=\"([0-9]+)\">/;
        my $matched;
        for my $postnum (@posts) {
            $matched = 1 if $l_postnum == $postnum;
        }
        next if $matched;
        print $temp "$line\n";
    }
    close $temp;
    close $read;
    rename "$board/$thread.tmp", "$board/res/$thread.html" || die "Cannot rename to thread file: $!";

    my ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject) = admin_thread_info($board, $thread);
    write_thread($dir, $board, $thread, $last_bumped, $last_posted, $closed, $permasage, $postcount, $subject);
}

sub delete_log_entries {
    my ($board, $thread, @posts) = @_;
    return unless -e "log.txt";
    open my $temp, '>:utf8', "log.tmp" || die "Cannot write temporary file: $!";
    flock $temp, LOCK_EX;
    open my $read, '<:utf8', "log.txt" || die "Cannot read log file: $!";
    flock $read, LOCK_SH;
    while (my $line = <$read>) {
        chomp $line;
        my ($l_board, $l_thread, $l_postnum) = $line =~ /^.*? [0-9]+ (.*?) ([0-9]+) ([0-9]+)/;
        my $matched;
        for my $postnum (@posts) {
            $matched = 1 if "$l_board$l_thread$l_postnum" eq "$board$thread$postnum";
        }
        next if $matched;
        print $temp "$line\n";
    }
    close $temp;
    close $read;
    rename "log.tmp", "log.txt" || die "Cannot rename to log file: $!";
}

sub delete_thread {
    my ($board, $thread) = @_;
    return unless -e "$board/res/$thread.html";
    unlink("$board/res/$thread.html");
}

sub delete_all {
    my $ip = shift;

    my %userposts = ();
    open my $temp, '>:utf8', "log.tmp" || die "Cannot write temporary file: $!";
    flock $temp, LOCK_EX;
    open my $read, '<:utf8', "log.txt" || die "Cannot read log file: $!";
    flock $read, LOCK_SH;
    while (my $line = <$read>) {
        chomp $line;
        my ($l_ip, $l_board, $l_thread, $l_postnum) = $line =~ /^(.*?) [0-9]+ (.*?) ([0-9]+) ([0-9]+)/;
        my $matched;
        if (RC4(SECRET_KEY, decode_base64($l_ip)) eq $ip) {
            push(@{$userposts{"$l_board,$l_thread"}}, $l_postnum);
            $matched = 1;
        }
        next if $matched;
        print $temp "$line\n";
    }
    close $temp;
    close $read;
    rename "log.tmp", "log.txt" || die "Cannot rename to log file: $!";

    foreach my $group (keys %userposts) {
        my ($board, $thread) = split(',', $group);
        delete_posts($board, $thread, @{$userposts{$group}});
    }
}

sub blacklist_ip {
    my $ip = shift;
    open my $append, '>>:utf8', 'ban.txt' || die "Cannot write ban file: $!";
    flock $append, LOCK_EX;
    print $append "$ip\n";
    close $append;
}