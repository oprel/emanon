use strict;
no strict 'refs';
use Encode qw/decode encode/;

sub board_settings($$){ # returns specialized board settings if they exist.
	my ($option, $board) = @_;
	my $optionpath = $option . '_' . uc $board;
	if (defined(&$optionpath)){return &$optionpath}else{return &$option};
}

sub read_thread_info($$) {
    my ($board, $thread) = @_;
    my ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject);
    open my $read, '<:utf8', "$board/res/$thread.html" || die "Cannot read thread file: $!";
    flock $read, LOCK_SH;
    my $line = <$read>;
    close $read;
    my $pattern = qr{^.*?<!--([0-9]+),([0-9]+),([01]),([01]),([0-9]+)--><title>(.*?)<\/title>};
    ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject) = $line =~ /$pattern/;
    return ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject);
}

sub admin_thread_info($$) { # admin use only, after deleting posts
    my ($board, $thread) = @_;
    my ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject);
    open my $read, '<:utf8', "$board/res/$thread.html" || die "Cannot read thread file: $!";
    flock $read, LOCK_SH;
    while (<$read>) {
        chomp;
        if (/^<div class=\"post\" id=\"([0-9]+)\"><!--([0-9]+),([01])-->/) {
            ($postcount, $last_posted, my $sage) = ($1, $2, $3);
            $last_bumped = $last_posted if $sage == 0;
        }
        elsif (/^.*?<!--[0-9]+,[0-9]+,([01]),([01]),[0-9]+--><title>(.*?)<\/title>/) {
            ($closed, $permasage, $subject) = ($1, $2, $3);
        }
    }
    close $read;

    return ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject);
}

sub read_dir($) {
    my $board = shift;
    opendir my $read, "$board/res/" || die "Cannot open directory: $!";
    my @thread_list = grep {/^[0-9]+\.html$/} readdir $read;
    closedir $read;
    return @thread_list;
}

sub read_thread_list($) {
    my $board = shift;
    return unless -d "$board/res/";
    my @thread_list;
    for (read_dir($board)) {
        /^([0-9]+)\.html$/;
        my $thread = $1;
        my ($last_bumped, $last_posted, $closed, $permasage, $postcount, $subject) = read_thread_info($board, $thread);
        push @thread_list, "$last_bumped $last_posted $thread $closed $permasage $postcount $subject";
    }
    return sort { $b cmp $a } @thread_list;
}

# post log

sub write_log($$$$$$) {
    my ($ip, $time, $board, $thread, $postcount, $sage) = @_;
    $ip = encode_base64(RC4(SECRET_KEY, $ip));
    open my $append, '>>:utf8', 'log.txt' || die "Cannot write log file: $!";
    flock $append, LOCK_EX;
    print $append "$ip $time $board $thread $postcount $sage\n";
    close $append;
}

sub read_log($$){
    my ($ip, $time) = @_;
    $ip = encode_base64(RC4(SECRET_KEY, $ip));
    my $log_time = 0;
    if (-e 'log.txt') {
        my $read = File::ReadBackwards->new('log.txt');
        while( defined( my $line = $read->readline ) ) {
            (my $log_ip, $log_time) = $line =~ /^(.*?) ([0-9]+)/;
            last if ($time - $log_time) > FLOOD_DELAY;
            last if $ip eq $log_ip;
        }
    }
    return $log_time;
}

# string manipulation

sub clean_string($) {
    my $str = shift;
    # uri unescape
    $str =~ s/\+/ /g;
    $str =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
    # clean string
    $str = decode('utf-8', $str);
    $str =~ s/[^\P{C}\n]//g; # remove all unicode control characters except \n
    $str =~ s/^[^\S\x{3000}]+|\s+$//g;
    $str =~ s/[^\S\n]+$//mg;
    $str =~ s/\n{3,}/\n\n/g;
    # html escape
    $str =~ s/&/&amp;/g;
    $str =~ s/</&lt;/g;
    $str =~ s/>/&gt;/g;
    $str =~ s/\"/&quot;/g; #"
    return $str;
}

sub parse_date($$) {
    my ($time, $board) = @_;
    my $date = scalar gmtime($time + ( board_settings("TIME_ZONE", $board) * 3600 )); # By hours
	my @month = qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec);
	my $ts = board_settings("TIME_SETTINGS", $board);
	if ($ts eq "READABLE"){	
		my @subst = qw(January February March April May June July August September October November December);
		for (my $i = 0; $i < 12; $i++) {
			$date =~ s/@month[$i]/@subst[$i]/;
		} #Wed May 27 11:01:45 2015
		$date =~ s/^[\w]+ ([\w]+) \s?([\d]+) ([0-9]+\:[0-9]+)\:[0-9]+ ([\d]+)$/$1 $2, $4 $3/;
		return $date;
	}elsif ($ts eq "DQN"){
		my $day = int(($time-746755200)/86400); #seconds since Sep 1993 converted to days
		$date =~ s/^[\w]+ ([\w]+) \s?([\d]+) ([0-9]+\:[0-9]+)\:[0-9]+ ([\d]+)$/$3/;
		return "1993-09-$day $date";
	}else{
		my @subst = qw(01 02 03 04 05 06 07 08 09 10 11 12);
		for (my $i = 0; $i < 12; $i++) {
			$date =~ s/@month[$i]/@subst[$i]/;
		}
		$date =~ s/^[\w]+ ([\d]+) \s?([\d]+) ([0-9]+\:[0-9]+)\:[0-9]+ ([\d]+)$/$4\-$1\-$2 $3/;
		$date =~ s/\-([0-9])\s/-0$1 /g;
		return $date;
	}
}

sub tripcode($) {
    my $name = shift;
    my ($tripkey, $secret) = (TRIP_KEY, SECRET_KEY);
    if ($name =~ /^(.*?)((?<!&)\#|\Q$tripkey\E)(.*)$/) {
        my ($namepart, $marker, $trippart) = ($1, $2, $3);
        my $trip;
		    if ($trippart =~ s/(?:\Q$marker\E)(?<!&\#)(?:\Q$marker\E)*(.*)$//) {
            use Digest::SHA1 'sha1';
            my $sha = encode_base64(pack("H*",sha1($1.$secret)));
            $sha = substr($sha,0,11);
            $sha =~ s/[^\.-z]/./g;
            $sha =~ tr/:;<=>?@[\\]^_`/ABCDEFGabcdef/;
            $trip = $tripkey . $tripkey . $sha;
            return ($namepart, parse_tripcode($trip)) unless $trippart;
		    }
        unless ($@) {
            #$trippart = decode("UTF-8", $trippart);
            $trippart = encode("Shift_JIS", $trippart, 0x0200);
        }
        my $salt = substr $trippart . "H..", 1, 2;
        $salt =~ s/[^\.-z]/./g;
        $salt =~ tr/:;<=>?@[\\]^_`/ABCDEFGabcdef/;
        $trip = $tripkey . (substr crypt($trippart, $salt), -10) . $trip;
        return ($namepart, parse_tripcode($trip));
    }
    return $name;
}

sub parse_tripcode($) {
    my $trip = shift;
    my %caps = CAPPED_TRIPS;
    while (my ($key, $cap) = each(%caps)) {
        $trip =~ s/$key/$cap/;
    }
    return $trip;
}

# extract data

sub form_data() {
    my (%input, $buffer);
    if (length ($ENV{'QUERY_STRING'}) > 0) {
        $buffer = $ENV{'QUERY_STRING'};
    }
    else {
        read STDIN, $buffer, $ENV{'CONTENT_LENGTH'};
    }
    my @pairs = split(/&/, $buffer);
    foreach my $pair (@pairs) {
        my ($name, $value) = split(/=/, $pair);
        $input{$name} = clean_string($value);
    }
    return %input;
}

sub include($) {
    my ($file) = @_;
    open my $read, '<', "$file";
    my $content = do { local $/; <$read> };
    close $read;
    $content =~ s/[\r\n]//g;
    return $content;
}

# checks

sub blacklist($$) {
    my ($str, $file) = @_;
    my $match = 0;
    open my $read, '<', "$file";
    flock $read, LOCK_SH;
    while (<$read>) {
        chomp;
        my $item = clean_string($_);
        $match = 1 if $str =~ /$item/gi;
    }
    close $read;
    return $match;
}

# misc

sub redirect($$$$$$) {
    my ($dir, $board, $thread, $postcount, $sage, $noko) = @_;
    if ($board) {
        if ($noko) {
            $dir .= "/read.cgi/$board/$thread";
            $dir .= "/l50" if $postcount > 50;
            #$dir .= "#$postcount";
        }
        else { $dir .= "/$board/" }
    }
    $dir = 'index.html' unless $dir;
    print
      "Content-type: text/html\n\n"
    , '<!DOCTYPE html>'
    , '<html><head>'
    , '<title>Updating...</title>'
    , '<meta http-equiv="refresh" content="' . board_settings("REDIRECT_DELAY", $board) . ';'
    , ' url=' . $dir . '?time=' . time . '">'
    , '</head><body>'
	;
	if (-e "$board/updating.html"){
	print include("$board/updating.html");}
	else{print 'Updating...'};
	print '</body></html>'
    ;
}

sub abort($) {
    my $msg = shift;
    print "Content-type: text/html\n\n";
    print '<strong>Error: ' . $msg . '</strong>';
    exit;
}

# cryptography

sub RC4 {
    my $MAX_CHUNK_SIZE = 1024;
    my $self;
    my (@state, $x, $y);
    if (ref $_[0]) {
        $self  = shift;
        @state = @{ $self->{state} };
        $x     = $self->{x};
        $y     = $self->{y};
    }
    else {
        @state = Setup(shift);
        $x = $y = 0;
    }
    my $message    = shift;
    my $num_pieces = do {
        my $num = length($message) / $MAX_CHUNK_SIZE;
        my $int = int $num;
        $int == $num ? $int : $int + 1;
    };
    for my $piece (0 .. $num_pieces - 1) {
        my @message = unpack "C*", substr($message, $piece * $MAX_CHUNK_SIZE, $MAX_CHUNK_SIZE);
        for (@message) {
            $x = 0 if ++$x > 255;
            $y -= 256 if ($y += $state[$x]) > 255;
            @state[ $x, $y ] = @state[ $y, $x ];
            $_ ^= $state[ ($state[$x] + $state[$y]) % 256 ];
        }
        substr($message, $piece * $MAX_CHUNK_SIZE, $MAX_CHUNK_SIZE) = pack "C*", @message;
    }
    if ($self) {
        $self->{state} = \@state;
        $self->{x}     = $x;
        $self->{y}     = $y;
    }
    $message;
}

sub Setup {
    my @k = unpack('C*', shift);
    my @state = 0 .. 255;
    my $y = 0;
    for my $x (0 .. 255) {
        $y = ($k[ $x % @k ] + $state[$x] + $y) % 256;
        @state[ $x, $y ] = @state[ $y, $x ];
    }
    wantarray ? @state : \@state;
}

sub encode_base64($) {
    my $data = shift;
    my $res = pack "u", $data;
    $res =~ s/^.//mg;
    $res =~ s/\n//g;
    $res =~ tr|` -_|AA-Za-z0-9+/|;
    my $padding = (3 - length($data) % 3) % 3;
    $res =~ s/.{$padding}$/'='x$padding/e if ($padding);
    $res =~ s/(.{1,76})/$1/g;
    return $res;
}

sub decode_base64($) {
    my $str = shift;
    $str =~ tr|A-Za-z0-9+=/||cd;
    $str =~ s/=+$//;
    $str =~ tr|A-Za-z0-9+/| -_|;
    return "" unless (length $str);
    return unpack "u", join '', map { chr(32 + length($_) * 3 / 4) . $_ } $str =~ /(.{1,60})/gs;
}

1;
