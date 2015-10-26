#!/usr/bin/perl -w

use strict;
use CGI::Carp 'fatalsToBrowser';
use Fcntl ':flock';
use lib '.';
use Time::Piece;

if (!-d "converted/") { mkdir("converted", 0755) || die "Cannot create directory: $!"; };
my @threadlist = read_dir("res");

print "Content-type: text/html\n\n";
foreach (@threadlist) {
    my $thread = $_;
    open my $read, '<:encoding(shift_jis)', "res/$thread" || die "Cannot read static file: $!";
    flock $read, LOCK_SH;
    my @raw = <$read>;
    my $html = join('',@raw);
    close $read;
    
my ($thread_id) = $html =~ /postform([0-9]+)\"/;
my ($title, $postcount) = $html =~ /<h2>(.*?) <small>\(([0-9]+)\)<\/small><\/h2>/;
my ($board) = $html =~ /<a href="\/([aA-zZ0-9]+)\/index.html">Return/;

$html =~ s/<div class=\"reply(?:.*)(?:&gt;|>>)([0-9]+)(?:.*?)a>(.*?)([0-9]+\-[0-9]+\-[0-9]+ [0-9:]+:[0-9:]+)/ our $timestamp = convert_time($3); '<div class="post" id="' . $1 . '"><!--' . $timestamp . ',0--><div class="posthead"><span class="num" onclick="quote(' . $1 . ',' . $timestamp . ')">' . $1 . $2 . $3/eg;#"
$html =~ s/class=\"poster/class=\"/g;
$html =~ s/<span class=\"deletebutton\">(.*)<\/h3>/<\/div>/g;
$html =~ s/class=\"replytext\"/class=\"comment\"/g;
$html =~ s/\/([aA-zZ]+)\/kareha\.pl/\/read\.cgi\/$1/g;
$html =~ s/<div class=\"aa\">(.*?)<\/div>/<span lang=\"ja\">$1<\/span>/g;

our $timestamp;
my $header = "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><meta id=\"meta\" name=\"viewport\" content=\"width=device-width; initial-scale=1.0\"><!--$timestamp,$timestamp,0,0,$postcount--><title>$title</title><script async src=\"/script.js\"></script><link rel=\"stylesheet\" title=\"default\" href=\"/style.css\"></head><body id=\"threadpage\"><div id=\"hover\"></div><div><span class=\"links\"><a href=\"/$board/\">Return</a> </span><hr><div class=\"subject\"><h2>$title</h2></div>";
my $footer = "<hr><span class=\"links\"><a href=\"/$board/\">Return</a> </span><div class=\"form $thread_id\"><form action=\"/post.cgi\" method=\"post\" id=\"form$thread_id\" onsubmit=\"set_cookie(name.value);this.reply.disabled=true\"><input type=\"hidden\" name=\"board\" value=\"$board\"><input type=\"hidden\" name=\"noko\" value=\"on\"><input type=\"hidden\" name=\"thread\" value=\"$thread_id\">Name: <input type=\"text\" name=\"name\"> <label><input type=\"checkbox\" name=\"sage\"><span></span> Sage</label> <input type=\"submit\" value=\"Preview\" name=\"reply\"> <input type=\"submit\" value=\"Reply\" name=\"reply\"> <br><textarea name=\"message\" rows=\"5\" cols=\"64\"></textarea><div class=\"hide\">Leave this field blank: <textarea rows=\"2\" name=\"comment\"></textarea></div></form></div></div></body></html>";

$html =~ s/(.*?)(?=\n<div class="post")/$header/s;
$html =~ s/<\/div> <\/div>  <form.*/$footer/;
    
    open my $write, '>:utf8', "converted/$thread_id.html" || die "Cannot write file: $!";
    flock $write, LOCK_EX;
    print $write "$html";
    close $write;
    print "Finished: $thread_id<br>";
} 
print 'DONE!';

sub read_dir($) {
    my $folder = shift;
    opendir my $read, "$folder/" || die "Cannot open folder: $!";
    my @thread_list = grep {/^[0-9]+\.html$/} readdir $read;
    #my @thread_list = grep {/^.*\.html$/} readdir $read;
    closedir $read;
    return @thread_list;
}

sub convert_time($) {
    my $time= shift;
    my ($year, $day, $hour, $minute) = $time =~ /([0-9]+)-(?:[0-9]+)-([0-9]+) ([0-9]+):([0-9]+)/;
    if ($year == 1993){
        return 746755200 + 60*(60*(24*($day)+$hour)+$minute); # eternal september magic
    }else{
        $time = Time::Piece->strptime($time, '%Y-%m-%d %H:%M');
        return $time->epoch;
    }
}