use strict;

use constant LANGUAGE_CODE => 'en';

sub print_preview($$$$$$$$;$$$) {
    my ($dir, $board, $name, $trip, $comment, $parsed_comment, $postcount, $sage, $subject, $newthread, $thread) = @_;
    $subject = encode('utf8', $subject);
    $name    = encode('utf8', $name);
    $comment = encode('utf8', $comment);
    $parsed_comment = encode('utf8', $parsed_comment);
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html lang="' . LANGUAGE_CODE . '">'
    , '<head>'
    , (-e "$board/meta.html") ? include("$board/meta.html") : include("meta.html")
    , '<title>Post Preview</title>'
    , '<script async src="' . $dir . '/script.js"></script>'
	, (board_settings("PRETTIFY_CODE", $board)) ? '<script async src="' . $dir . '/run_prettify.js"></script>' : ''
	, stylesheets($dir, $board)
    , '</head>'
    , '<body id="threadpage">'
    , '<div class="links"><a href="' . $dir . '/' . $board . '">Return</a> '
    , $newthread ? '' : '<a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . '">Entire thread</a> '
    , $postcount > 50 ? '<a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . '/l50">Last 50 posts</a> ' : ''
    , $postcount > 100 ? '<a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . '/1-100">1-100</a> ' : ''
    , '</div><br/>'
    , '<h1 style="color:red;font-weight:normal;margin:0 0 0.5em">Post Preview</h1>'
    , $newthread ? "Subject: $subject<br>" : ''
    , "Name: <strong>$name</strong> $trip<br>"
    , 'Comment: <br>'
    , '<div class="comment">' . $parsed_comment . '</div>'
    , '<div class="form">'
    , '<form action="' . $dir . '/post.cgi" method="post" onsubmit="set_cookie(name.value,\'name\');this.reply.disabled=true">'
    , '<input type="hidden" name="board" value="' . $board . '">'
    , '<input type="hidden" name="noko" value="on">'
    , $newthread ? '' : '<input type="hidden" name="thread" value="' . $thread . '">'
    , '<table>'
    , $newthread ? '<tr><td>Subject:</td><td><input type="text" name="subject" style="width:80%" value="' . $subject . '"></td></tr>' : ''
    , '<tr>'
    , '<td>Name:</td><td><input type="text" name="name"> '
	, $newthread ? '' : ('<label><input type="checkbox" name="sage"' , $sage ? ' checked="checked"' : '' , '><span></span> Sage</label> ')
	, '<input type="submit" value="Preview" name="reply"> ' 
    , '<input type="submit" value="' , $newthread ? 'Create new thread' : 'Reply' , '" name="reply"> '
    , '</tr>'
    , '</table>'
    , '<div class="hide">Leave this field blank:<textarea rows="2" name="comment"></textarea>Comment:</div>'
    , '<textarea name="message" rows="5" cols="64">' . $comment . '</textarea>'
    , '</form>'
    , '</div>'
    , '</body>'
    , '</html>'
    ;
    exit;
}

sub write_thread($$$$$$$$$;$$$$$) {
    my ($dir, $board, $thread, $last_bumped, $last_posted, $closed, $permasage, $postcount, $subject, $name, $trip, $time, $sage, $parsed_comment) = @_;
    if ($time) {
        $last_bumped = $time unless $sage;
        $last_posted = $time;
    }
	
    open my $temp, '>:utf8', "$board/$thread.tmp" || die "Cannot write temporary file: $!";
    flock $temp, LOCK_EX;
    open my $read, '<:utf8', "$board/res/$thread.html" || die "Cannot read thread file: $!";
    flock $read, LOCK_SH;
    print $temp
      '<!DOCTYPE html>'
    , '<html lang="' . LANGUAGE_CODE . '">'
    , '<head>'
    , (-e "$board/meta.html") ? include("$board/meta.html") : include("meta.html")
    , '<!--' . $last_bumped . ',' . $last_posted . ',' . $closed . ',' . $permasage . ',' . $postcount . '-->'
    , '<title>' . $subject . '</title>'
    , '<script async src="' . $dir . '/script.js"></script>'
	, (board_settings("PRETTIFY_CODE", $board)) ? '<script async src="' . $dir . '/run_prettify.js"></script>' : ''
    , stylesheets($dir, $board)    
	, '</head>'
    , '<body id="threadpage">'
	, '<div id="hover"></div>'
    , '<div><span class="links">'
    ;
    print_postlinks($temp, $dir, $board, $thread, $postcount, 'header');
    print $temp
      '</span><hr>'
    , '<div class="subject">'
    , '<h2>' . $subject . '</h2>'
    , '</div>'
    , "\n"
    ;
    while (my $line = <$read>) {
        chomp $line;
        my ($l_postnum, $l_time, $l_sage) = $line =~ /^<div class=\"post\" id=\"([0-9]+)\"><!--([0-9]+),([01])-->/;
        my ($l_name)    = $line =~ /<span class=\"name(?:.*?)\">(.*?)<\/span>/;
        my ($l_trip)    = $line =~ /<span class=\"trip\">(.*?)<\/span>/;
        my ($l_comment) = $line =~ /<div class=\"comment\">(.*?)<\/div>/;
        print_reply($temp, $dir, $board, $thread, $l_postnum, $l_name, $l_trip, $l_time, $l_sage, $l_comment, $postcount, $parsed_comment) if $l_postnum;
    }
    if (length $parsed_comment > 0) {
        print_reply($temp, $dir, $board, $thread, $postcount, $name, $trip, $time, $sage, $parsed_comment);
    }
    print $temp '<hr><span class="links">';
    print_postlinks($temp, $dir, $board, $thread, $postcount, 'footer');
	print $temp '</span>';
    print_postform($temp, $dir, $board, $thread, $postcount, $closed, 1);
    print $temp
      '</div>'
    , '</body>'
    , '</html>'
    ;
    close $temp;
    close $read;
    rename "$board/$thread.tmp", "$board/res/$thread.html" || die "Cannot rename to thread file: $!";
}

sub build_pages($$) {
    my ($dir, $board) = @_;
    my @thread_list = read_thread_list($board);
    my $title;
    my %boards = BOARDS;
    while (my ($key, $value) = each(%boards)) {
        $title = $value if $key eq $board;
    }

    open my $write, '>:utf8', "$board/index.html" || die "Cannot write index file: $!";
    flock $write, LOCK_EX;
    print $write
      '<!DOCTYPE html>'
    , '<html lang="' . LANGUAGE_CODE . '">'
    , '<head>'
    , (-e "$board/meta.html") ? include("$board/meta.html") : include("meta.html")
    , '<title>' . $title . '</title>'
	, '<script async src="' . $dir . '/isotope.pkgd.min.js"></script>'
    , '<script async src="' . $dir . '/script.js"></script>'
	, (board_settings("PRETTIFY_CODE", $board)) ? '<script async src="' . $dir . '/run_prettify.js"></script>' : ''
    , stylesheets($dir, $board)   
    , '</head>'
    , '<body id="frontpage">'
	, (-e "$board/header.html") ? '<div class="header shell"><div><span id="top" class="quickscroll"><a href="#bottom" title="Jump to bottom">&#9660;</a></span>' . include("$board/header.html") . '</div></div>' : ''
    , '<div class="shell">'
	, '<div class="boardnav">'
	, board_navigation($dir, $board)
	, '</div><div id="options" class="optionmenu hide">'
	, include("options.html") . '&#8203;</div>'
	, '</div><div class="grid">'
	;

    my $i = 0;
    my $max_threads = $#thread_list > (PAGE_THREADS - 1) ? (PAGE_THREADS - 1) : $#thread_list;
    for (@thread_list[ 0 .. $max_threads ]) {
        /^([0-9]+) ([0-9]+) ([0-9]+) ([01]+) ([01]+) ([0-9]+) (.*)$/;
        my ($thread, $closed, $permasage, $postcount, $subject, $last_bumped, $last_posted) = ($3, $4, $5, $6, $7, $1, $2);
        $i++;
        my $a = $postcount > 100 ? '/1-100' : '';
        print $write
          '<div id="' . $thread . '" class="shell-thread">'
        , '<div>'
        , '<div class="subject">'
        , '<span class="threadpost">[' . $i . ':' . $postcount
		, (board_settings("TIME_SETTINGS", $board) eq 'SAGERU') ? '' : (
		  '<span class="sortinfo hide">:<span class="lastbump">' . $last_bumped . '</span>'
		  , ':<span class="lastpost">' . $last_posted . '</span>'
		  , ':<span class="threadage">' . $thread . '</span>'
		  , ':<span class="postcount">' . $postcount . '</span></span>')	
		, ']</span> '
        , '<h2>'
        , "<a href=\"$dir/read.cgi/$board/$thread\">" . $subject . '</a>'
        , '</h2>'
        , '</div>'
		;

        # retrieve first and most recent posts for the front page display
        my (@post_list, $post_recent);
        my $l = 0;
	    my $readback = File::ReadBackwards->new("$board/res/$thread.html") || die "Cannot read thread file: $!";
        while( defined( my $line = $readback->readline ) ) {
            $l++;
            chomp $line;
            $line = decode('utf8', $line);
            if ($l == 1) { next }
            elsif ($l > 1 && $l <= (PAGE_POSTS + 2)) { unshift @post_list, $line }
            elsif ($l == (PAGE_POSTS + 4)) { shift @post_list; $post_recent = 1; last }
        }
        if ($l <= PAGE_POSTS + 2) { shift @post_list }
        if ($post_recent) {
            my $a = $postcount > 100 ? '/1-100' : '';
            unshift @post_list,
              '<div class="recent">'
            , 'The ' . PAGE_POSTS . ' newest replies are shown below.<br>'
            , '<a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . $a
            , '">Read this thread from the beginning.</a>'
            , '</div>'
            ;
            my $n = 0;
            open my $read, '<:utf8', "$board/res/$thread.html" || die "Cannot read thread file: $!";
            flock $read, LOCK_SH;
            while (my $line = <$read>) {
                $n++;
                chomp $line;
                if ($n == 2) { unshift @post_list, $line; last }
            }
            close $read;
        }

        # print first and most recent posts after processing
        for my $line (@post_list) {
            my ($postnum) = $line =~ /^<div class=\"post\" id=\"([0-9]+)\"/;
            $line =~ s/^<div class=\"post\" id=\"[0-9]+\"><!--.*?-->/<div class=\"post\">/; #"
            $line = post_truncate($line, $dir, $board, $thread, $postnum) if POST_TRUNCATE;
            print $write $line;
        }
        print_postform($write, $dir, $board, $thread, $postcount, $closed, 0);
        print_postlinks($write, $dir, $board, $thread, $postcount, 'front');
        print $write '</div></div>';
    }
    print $write 
	  '</div><div class="footer">'
	, '<div id="threadlist" class="shell">'
    , '<div><div>'
    ;
    my $i = 0;
    my $max_threadlist = $#thread_list > (board_settings("PAGE_THREADLIST", $board) - 1) ? (board_settings("PAGE_THREADLIST", $board) - 1) : $#thread_list;
    for (@thread_list[ 0 .. $max_threadlist ]) {
        /^([0-9]+) ([0-9]+) ([0-9]+) ([01]) ([01]) ([0-9]+) (.*)$/;
        my ($thread, $postcount, $subject) = ($3, $6, $7);
        $i++;
        my $a = $postcount > 50 ? '/l50' : '';
        print $write
          ''
        , $i < (board_settings("PAGE_THREADS", $board) + 1)
            ? "<a href=\"$dir/read.cgi/$board/$thread$a\">$i: </a><a href=\"#$thread\" class=\"thread\">$subject ($postcount)</a>"
            : "<a href=\"$dir/read.cgi/$board/$thread$a\" class=\"thread\">$i: $subject ($postcount)</a>"
        , ' '
        ;
    }
    print $write
      '</div>'
    , '<div class="links">'
    , '<a href="' . $dir . '/' . $board . '/all">View all Threads</a>'
    , '</div></div>'
    , '</div>'
	;
	print_postform($write, $dir, $board);
	print $write
	  '</body>'
    , '</html>'
    ;
    close $write;

    open my $write, '>:utf8', "$board/subback.html" || die "Cannot write subback file: $!";
    flock $write, LOCK_EX;
    print $write
      '<!DOCTYPE html>'
    , '<html lang="' . LANGUAGE_CODE . '">'
    , '<head>'
    , (-e "$board/meta.html") ? include("$board/meta.html") : include("meta.html")
    , '<title>All Threads</title>'
    , '<script async src="' . $dir . '/script.js"></script>'
    , stylesheets($dir, $board)
    , '</head>'
    , '<body id="subback">'
    , '<div class="links shell"><div>'
    , '<a href="' . $dir . '/' . $board . '"/><h1>' . $board . '</h1></a>&emsp;'
    , '</div></div>'
    , '<div class="shell"><div>'
    , '<table class="threads"><thead><tr><th width="10%">#</th><th nowrap="nowrap" width="100%">Subject</th><th nowrap="nowrap">Posts</th><th nowrap="nowrap">Last Post</th></tr></thead><tbody>'
    ;
    my $i = 0;
    for (@thread_list) {
        /^([0-9]+) ([0-9]+) ([0-9]+) ([01]+) ([01]+) ([0-9]+) (.*)$/;
        my ($thread, $postcount, $subject, $last_posted) = ($3, $6, $7, $2);
        $i++;
        my $a = $postcount > 50 ? '/l50' : '';
	print $write "<tr><td><a href=\"$dir/read.cgi/$board/$thread$a\">$i</a></td><td><a href=\"$dir/read.cgi/$board/$thread$a\" class=\"thread\">$subject</a></td><td>$postcount</td><td>" . parse_date($last_posted, $board) . "</td></tr>";
    }
    print $write
      '</tbody></table>'
    , '</div></div>'
    , '</body>'
    , '</html>'
    ;
    close $write;
}

# html utilities

sub print_reply($$$$$$$$$$;$$) {
    my ($fh, $dir, $board, $thread, $postnum, $name, $trip, $time, $sage, $comment, $newpost, $newcom) = @_;
    # Do NOT edit or remove hashbang lines!
	my $timesettings = board_settings("TIME_SETTINGS", $board);
    print $fh
      '<div class="post" id="' . $postnum . '"><!--' . $time . ',' . $sage . '-->' #! Must always be first line
    , '<div class="posthead">'
    , '<span class="num" onclick="quote(' . $postnum . ',' . $thread . ')">' . $postnum . '</span> '
    , 'Name: '
    , '<span class="name',board_settings("SHOW_SAGE", $board) && $sage?' sage':'','">' . $name . '</span>' #!
    , ' '
    , '<span class="trip">' . $trip . '</span> ' #!
	, ($timesettings eq 'SAGERU') ? '' : '<span class="time">' . parse_date($time, $board) . '</span>'
	, '</div>'
    , backlinks($dir, $board, $thread, $postnum, $newpost, $newcom)
    , '<div class="comment">' . $comment . '</div>' #!
    , '</div>'
    , "\n"
    ;
}

sub backlinks($$$$$) {
    my ($dir, $board, $thread, $postnum, $newpost, $newcom) = @_;
    return unless $newpost;
    my ($str, @arr);
	  my $back = File::ReadBackwards->new("$board/res/$thread.html");
    while( defined( my $line = $back->readline ) ) {
        my ($replynum, $comment) = $line =~ /^<div class=\"post\" id=\"([0-9]+)\">.*?<div class=\"comment\">(.*?)<\/div>/;
        last if $replynum == $postnum;
        unshift @arr, $replynum if $comment =~ /&gt;&gt;(?:[0-9\-,]+,)*$postnum(?:,[0-9\-,]*)*<\/a>/;
    }
    if ($newcom) {
        push @arr, $newpost if $newcom =~ /&gt;&gt;(?:[0-9\-,]+,)*$postnum(?:,[0-9\-,]*)*<\/a>/;
    }
    $str = join(',', @arr);
    if ($str) {
        $str =
          '<div class="backlinks">'
        . 'Quoted by: '
        . "<a href=\"$dir/read.cgi/$board/$thread/$str\" onmouseover=\"set_hover(\'$str\')\" onmouseout=\"reset_hover()\">&gt;&gt;$str</a>"
        . '</div>'
        ;
    }
    return $str;
}

sub print_postform($$$;$$$$) {
    my ($fh, $dir, $board, $thread, $postcount, $closed, $noko) = @_;
    print $fh $thread == 0 ? '<div class="form shell" id="newthread">' : '<div class="form ' . $thread . '">';
    if ($closed) {
        print $fh "<strong>This thread is closed. You can't reply anymore.</strong>";
    }
    elsif ($postcount >= board_settings("POST_LIMIT", $board)) {
        print $fh "<strong>This thread has reached the post limit. You can't reply anymore.</strong>";
    }
    elsif ($thread == 0) {
        print $fh
          '<div id="threadform">'
		, '<span id="bottom" class="quickscroll"><a href="#top" title="Jump to top">&#9650;</a></span>'
        , '<h2>New Thread</h2>'
        , '<form action="' . $dir . '/post.cgi" method="post" onsubmit="set_cookie(name.value,\'name\');this.reply.disabled=true">'
        , '<input type="hidden" name="board" value="' . $board . '">'
        , '<table>'
        , '<tr>'
        , '<td>Subject:</td><td><input type="text" name="subject" style="width:80%"></td>'
        , '</tr>'
		, '<tr>'
		, '<td>Name:</td><td><input type="text" name="name"' , (board_settings("FORCE_ANON", $board)) ? ' disabled' : '' , '> '
		, '<input type="submit" value="Create new thread" name="reply"> '
		, '<input type="submit" value="Preview" name="reply"> '
        , '</tr>'
        , '</table>'
        , '<textarea name="message" rows="5" cols="64"></textarea>'
		, '<div class="hide">Leave this field blank:<textarea rows="2" name="comment"></textarea></div>'
        , '</form>'
        , '</div>'
        ;
    }
    else {
        print $fh
          '<form action="' . $dir . '/post.cgi" method="post" id="form' . $thread . '" onsubmit="set_cookie(name.value,\'name\');this.reply.disabled=true">'
        , '<input type="hidden" name="board" value="' . $board . '">'
        , $noko ? '<input type="hidden" name="noko" value="on">' : ''
        , '<input type="hidden" name="thread" value="' . $thread . '">'
		, 'Name: <input type="text" name="name"' , (board_settings("FORCE_ANON", $board)) ? ' disabled' : '' , '> '
        , '<label><input type="checkbox" name="sage"><span></span> Sage</label> '
		, '<input type="submit" value="Preview" name="reply"> '
		, '<input type="submit" value="Reply" name="reply"> '
        , '<br>'
        , '<textarea name="message" rows="5" cols="64"></textarea>'
	    , '<div class="hide">Leave this field blank: <textarea rows="2" name="comment"></textarea></div>'
        , '</form>'
        ;
    }
    print $fh '</div>';
}

sub print_postlinks($$$$$$) {
    my ($fh, $dir, $board, $thread, $postcount, $page) = @_;
    if ($page eq 'front' || $page eq 'footer') {
        print $fh
          $page eq 'front' ? '<div class="links"><a class="quickreplytoggle hide" onclick="quick_reply(' . $thread . ')">Reply</a>  <a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . '">Entire thread</a> <a class="threadlistlink" href="#threadlist">Thread list</a>' : '<a href="' . $dir . '/' . $board . '/">Return</a> '
        , $postcount > 50  ? '<a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . '/l50">Last 50 posts</a> ' : ''
        , $postcount > 100 ? '<a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . '/1-100">1-100</a> ' : ''
		, $page eq 'front' ? '</div>' : ''
        ;
    }
    elsif ($page eq 'header') {
        print $fh
          '<a href="' . $dir . '/' . $board . '/">Return</a> '
        , $postcount > 50 ? '<a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . '/l50">Last 50 posts</a>' : ''
        , $postcount > 100 ? '<br><small>Pages: ' . pagination($dir, $board, $thread, $postcount) . '</small>' : ''
        ;
    }
}

sub stylesheets($$){
	my ($dir, $board) = @_;
    my $css = -e "$board/" . PAGE_CSS ? "$board/" . PAGE_CSS : PAGE_CSS;
	my $a = '<link rel="stylesheet" title="default" href="' . $dir . '/' . $css . '">';
	if (defined(ALT_CSS)){
		my %altsheets = ALT_CSS;
		foreach my $name (sort keys %altsheets) {
			$a .= '<link rel="stylesheet" disabled title="' . $name . '" href="' . $dir . '/' . $altsheets{$name} . '">';
		}
	}
	return $a;
}

sub board_navigation($$){
	my ($dir, $board) = @_;
	my @rawboards = BOARDS;
    my (@boards, $i);
        push(@boards, $rawboards[$_*2]) for 0..int(@rawboards/2)-1;
	my ($n, $menu);
	my $menu .= '<form name="boardselector"><select name="SelectURL" onChange="document.location.href=document.boardselector.SelectURL.options[document.boardselector.SelectURL.selectedIndex].value">';
	   $menu .= '<option value="' . $dir . '/all.cgi">[all] Recent Posts' if (-e "all.cgi");
	foreach my $name (@boards) {
        $i++;
		$menu .= '<option value="' . $dir . '/' . $name . '" ';
		$menu .= 'selected' if ($name eq $board);
		$menu .= '>/' . $name . '/ ' . $rawboards[$i*2-1];	
	}
	$menu .= '</select></form><span class="boardbar">';
	$menu .= '<span>[ <a href="' . $dir . '/all.cgi">all</a> ]</span>' if (-e "all.cgi");
	$menu .= '<span class="boards">[ ';
	foreach my $name (@boards) {
		$menu .= ' / ' if ($n != 0);
		$menu .= ($name eq $board) ? $name : '<a class="' . $name . '" href="' . $dir . '/' . $name . '/">' . $name . '</a>';
		$n++;
	}
	$menu .= ' ]</span>';
    $menu .= '<span>[ <a href="images/">Images</a> ]</span>' if (-e "images/index.html");    
    $menu .= '</span><span class="right">';
	$menu .= '<span>[ <a href="$board/images/">Images</a> ]</span>' if (-e "$board/images/index.html");
	$menu .= '<span class="optiontoggle hide">[ <a onclick="toggle_class(\'optionmenu\', \'hide\')">Options</a> ]</span>'
	      .  '<span>[ <a href="' . $dir . '/">Home</a> ]</span></span>';
	return $menu;
}

sub pagination($$$$) {
    my ($dir, $board, $thread, $postcount) = @_;
    my $str;
    my $pages = $postcount / 100;
    $pages = int($pages) + 1 if int($pages) != $pages;
    for (my $count = 1; $count <= $pages; $count++) {
        my $last   = $count * 100;
        my $first  = $last - 99;
        $last = '' if $last > $postcount;
        $str .= "<a href=\"$dir/read.cgi/$board/$thread/$first-$last\">$first-$last</a> ";
    }
    return $str;
}

sub post_truncate($$$$$) {
    my ($line, $dir, $board, $thread, $postnum) = @_;
    my $truncate = board_settings("POST_TRUNCATE", $board) - 1;
    my ($comment) = $line =~ /<div class=\"comment\">((?:.+?<(?:br|\/?p|\/?blockquote)>)(?:.*?<(?:br|\/?p|\/?blockquote)>){$truncate})/;
    return $line if (length $comment == 0);
    $comment =~ s/(?:<br>)+$//;

    # close open tags
    my @tag_list;
    while ($comment =~ /<([a-z]+)(?: .*?)?>/g) {
        next if $1 eq 'br';
        unshift @tag_list, $1;
    }
        for my $tag (@tag_list) {
        $comment .= "</$tag>";
    }
    for my $tag (reverse @tag_list) {
        my $balance;
        $balance++ while $comment =~ /<\/$tag>/g;
        $balance-- while $comment =~ /<$tag(?: .*?)?>/g;
        if ($balance) {
            for (1 .. $balance) {
                $comment =~ s/^(.*)<\/$tag>(.*)$/$1$2/;
            }
        }
    }
    unless ($comment =~ /<\/(?:p|blockquote)>$/) { $comment .= '<br><br>' }
    $comment .= '<em>(<a href="' . $dir . '/read.cgi/' . $board . '/' . $thread . '/' . $postnum . '">Post truncated</a>)</em>';
    $line =~ s/<div class=\"comment\">.*?<\/div>/<div class=\"comment\">$comment<\/div>/;
    return $line;
}

sub prettify($) {
    my $dir = shift;
    return '<script src="' . $dir . '/run_prettify.js?autoload=true"></script>' if -e "run_prettify.js";
}

1;
