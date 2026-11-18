foreach command {ord::openroad_version ord::openroad_git_describe} {
 if {[llength [info commands $command]]} {puts "$command [catch {$command} value] $value"} else {puts "$command UNAVAILABLE"}
}
