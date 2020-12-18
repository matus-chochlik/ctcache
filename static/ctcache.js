formatDuration = function(sec) {
    if (sec > 604800) {
        return (sec / 604800).toFixed(0) + ' wk';
    }
    if (sec > 86400) {
        return (sec / 86400).toFixed(0) + ' dy';
    }
    if (sec > 3600) {
        return (sec / 3600).toFixed(0) + ' hr';
    }
    if (sec > 60) {
        return (sec / 60).toFixed(0) + ' min';
    }
    return sec.toFixed(0) + ' sec';
};

formatRatio = function(x) {
    return (x * 100.0).toFixed(0) + '%'
};

reloadStats =
    function() {
    $.getJSON('/stats?' + new Date().getTime(), function(stats) {
        $('#hit_rate_value').text(formatRatio(stats.total_hit_rate));
        $('#cached_count_value').text(stats.cached_count);
        $('#cleaned_count_value').text(stats.cleaned_count);
        $('#saved_ago_value').text(formatDuration(stats.saved_seconds_ago));
        $('#uptime_value').text(formatDuration(stats.uptime_seconds));
    });
}

var isActive = false;
var statReloadCount = 0;
var hitsReloadCount = 0;
var daysReloadCount = 0;

doReload = function() {
    statReloadCount += 1;
    if (isActive || statReloadCount >= 10) {
        reloadStats();
        statReloadCount = 0;
    }

    hitsReloadCount += 1;
    if (isActive || hitsReloadCount >= 100) {
        $('#hits_histogram')
            .attr('src', '/image/hits_histogram.svg?' + new Date().getTime())
        hitsReloadCount = 0;
    }

    daysReloadCount += 1;
    if (isActive || daysReloadCount >= 1200) {
        $('#days_histogram')
            .attr('src', '/image/days_histogram.svg?' + new Date().getTime())
        daysReloadCount = 0;
    }
};

$(window).focus(function() {
    isActive = true;
    doReload();
});

$(window).blur(function() {
    isActive = false;
    statReloadCount = 0;
    hitsReloadCount = 0;
    daysReloadCount = 0;
});


setInterval(doReload, 6000);


document.addEventListener('DOMContentLoaded', reloadStats);
