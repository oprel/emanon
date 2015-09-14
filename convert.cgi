#!/usr/bin/perl -Tw

use strict;
use CGI::Carp 'fatalsToBrowser';
use Fcntl ':flock';
use File::ReadBackwards;
use lib '.';

open my $read, '<', "all.html" || die "Cannot read static file: $!";
flock $read, LOCK_SH;
my $html = <$read>;
close $read;
my $postcount = $html =~ /<i>([0-9]+) replies<\/i>/
my $lastpost = $html =~ /<div class=\"post ([0-9]+)\" id=\"$postcount\">

$html =~ s/<!--([0-1)])([0-1)])-->/<!--$lastpost,$lastpost,$1,$2,$postcount-->/; #threadinfo

$html =~ s/<div class=\"post ([0-9]+)\" id=\"([0-9]+)\">/<div class=\"post\" id=\"$2\"<!--$1,0-->/; #posthead
$html =~ s/<div class=\"postbody\">/<div class=\"comment\">/; #postbody
$html =~ s/<div id=\"airmail-line\"(.*?)<\/i><\/div>//; #airmail-line
$html =~ s/<div id=\"mailing\">(.*?)<\/div><\/div><\/div>//

print "Content-type: text/html\n\n"	. $static;
