#!/usr/bin/perl -Tw

use strict;
use CGI::Carp 'fatalsToBrowser';
use Encode qw/decode/;
use Fcntl ':flock';

sub form_data() {
    my (%input, $buffer);
    if (length ($ENV{'QUERY_STRING'}) > 0) {
        $buffer = $ENV{'QUERY_STRING'};
    }
    my @pairs = split(/&/, $buffer);
    for my $pair (@pairs) {
        my ($name, $value) = split(/=/, $pair);
        $input{$name} = uri_unescape($value);
    }
    return %input;
}

sub abort($) {
    my $msg = shift;
    print "Content-type: text/html\n\n";
    print '<strong>Error: ' . $msg . '</strong>';
    exit;
}

my $time   = time;
my %form   = form_data();
my $board  = $form{'board'};
my $thread = $form{'thread'};
my $posts  = $form{'read'};
my $dir    = $ENV{'SCRIPT_NAME'};

($board )  = $board  =~ /^([a-z]+)$/;
($thread)  = $thread =~ /^([0-9]+)$/;
($posts)   = $posts  =~ /^([0-9l\-\,]+)$/;
($dir)     = $dir    =~ /^(.*)\/[^\/]*$/;

abort('Board not defined') if !$board;
abort('Board does not exist') if !-d "$board/";
abort('Thread does not exist') unless -e "$board/res/$thread.html";
abort('Invalid posts') if !$thread || !$posts;

my @list = split(/\,/, $posts);
my (@post_list, $header, $footer, $max_post, $max_range);
open my $read, '<', "$board/res/$thread.html" || die "Cannot read thread file: $!";
flock $read, LOCK_SH;
print "Content-type: text/html\n\n";
while (my $line = <$read>) {
    chomp $line;
    $line =~ s/<!--.*?->//g;
    if ($line =~ /^<div class=\"post\" id=\"([0-9]+)\">/) {
        my ($postnum) = $line =~ /^<div class=\"post\" id=\"([0-9]+)\">/;
        $max_post = $postnum;
        if ($list[0] =~ /^l[0-9]+$/) {
            my ($last) = $list[0] =~ /^l([0-9]+)$/;
            $last = 80 if $last > 80;
			$line =~ s/<!--(.*?)->//g;
            push @post_list, $line;
            shift @post_list if @post_list > $last;
        }
        else {
            for (@list) {
                my $item = $_;
                if ($item =~ /^[0-9]+$/) {
                    if ($postnum == $item) {
                        print $line;
                        last;
                    }
                }
                elsif ($item =~ /^[0-9]+-[0-9]*$/) {
                    my ($lower, $upper) = $item =~ /^([0-9]+)-([0-9]*)$/;
                    $upper = $postnum + 1 unless $upper;
                    if ($postnum >= $lower && $postnum <= $upper) {
                        $max_range = $postnum;
                        print $line;
                        last;
                    }
                }
            }
        }
    }
    else {
        $line =~ s{Return<\/a> }{Return</a> <a href=\"$dir/read.cgi/$board/$thread\">Entire thread</a> } unless $posts eq '1-' ;#"
        if ($header) {
            $footer = $line;
        }
        else {
            $header = 1;
            print $line;
        }
    }
}
close $read;
if ($max_post > 100 && $max_range) {
    my $next_lower = $max_range + 1;
    my $next_upper  = $max_range + 100;
    $next_upper = '' if $next_upper > $max_post;
    if ($next_lower <= $max_post) {
        $footer =~ s{1-100</a>}{1-100</a> <a href=\"$dir/read.cgi/$board/$thread/$next_lower-$next_upper\">Next 100 posts</a>};#"
    }
}
$footer =~ s/<!--(.*?)->//g;
print @post_list;
print $footer;
exit;

sub uri_unescape($) {
    my $str = shift;
    $str =~ s/\+/ /g;
    $str =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
    $str = decode('utf8', $str);
    return $str;
}