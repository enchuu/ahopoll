window.onload = function () {
    var settings = {};
    settings.max_points = 100;
    settings.colors= ["blue", "red", "green", "gray", "purple", "orange", "brown", "cadetblue"]
    var data = processData(votes, settings);
    var lines = makeLines(data);
    drawLines(lines, settings);
    var toggles = document.getElementsByClassName("toggle");
    for (var i = 0; i < toggles.length; i++) {
        (function(i) {
            toggles[i].onclick = function() { toggleAll(i) };
        })(i);
    }
}

function clone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

function processData(votes, settings) {
    var data = [];
    var entrees = document.getElementsByClassName("entree");
    data[0] = { "time": creation_time, "counts": [] };
    var count = data[0].counts;
    for (var i = 0; i < entrees.length; i++) {
        var qo = entrees[i].id.split(",");
        var q = qo[0],
            o = qo[1];
        if (!count[q]) {
            count[q] = [];
        }
        count[q][o] = 0;
    }
    var i, j = 0;
    var ticks = Math.min(votes.length, settings.max_points);
    var votesPerTick = votes.length / ticks;
    for (i = 1; i <= ticks; i++) {
        data[i] = {}
        data[i].time = votes[j].time;
        data[i].counts = clone(data[i-1].counts);
        var count = data[i].counts;
        for (; j < i * votesPerTick; j++) {
            var vote = votes[j].vote;
            for (var k = 0, keys = Object.keys(vote); k < keys.length; k++) {
                var q = vote[keys[k]];
                for (var l = 0; l < q.length; l++) {
                    count[k][q[l]]++;
                }
            }
        }
    }
    return data;
}

function getCoordsMaker(data) {
    var total_votes = votes.length;
    var max_votes = [];
    var last_vote = data[data.length - 1].counts;
    for (var i = 0; i < last_vote.length; i++) {
        max_votes[i] = 0;
        for (var j = 0; j < last_vote[i].length; j++) {
            if (last_vote[i][j] > max_votes[i]) {
                max_votes[i] = last_vote[i][j];
            }
        }
    }
    var graphs = document.getElementsByClassName("graphcontainer");
    var graph = graphs[0];
    var height = graph.clientHeight;
    var height = 300;
    var width = graph.clientWidth;
    function getCoords(i, q, count) {
        var x = (i) / total_votes * width;
        var y = height - (count / max_votes[q]) * height * .98;
        return " L " + x + " " + y;
    }
    return getCoords;
}

function makeLines(data) {
    var lines = [];
    var coordsMaker = getCoordsMaker(data);
    var graphs = document.getElementsByClassName("graphcontainer");
    var graph = graphs[0];
    var height = graph.clientHeight;
    height = 300;
    for (var i = 0; i < data[0].counts.length; i++) {
        lines[i] = [];
        for (var j = 0; j < data[0].counts[i].length; j++) {
            lines[i][j] = "M 0 " + height;
        }
    }
    for (var i = 1; i < data.length; i++) {
        var time = data[i].time;
        var counts = data[i].counts;
        for (var j = 0; j < counts.length; j++) {
            for (var k = 0; k < counts[j].length; k++) {
                if (i == data.length - 1 || counts[j][k] != data[i-1].counts[j][k]
                        || counts[j][k] == 0) {
                    lines[j][k] += coordsMaker(i, j, counts[j][k]);
                }
            }
        }
    }
    return lines;
}

function toggle(id) {
    var item = document.getElementById(id);
    var element = document.getElementById(id + "path");
    if (element.style.display == "none") {
        element.style.display = "inline";
        item.style.color = "black";
    }
    else {
        element.style.display = "none";
        item.style.color = "gray";
    }
}

function toggleAll(q) {
    for (var i = 0; i < document.getElementById(q + 1 + "table").children[0].children.length; i++) {
        toggle(q + "," + i);
   }
}

function drawLines(lines, settings) {
    var graphs = document.getElementsByClassName("graph");
    for (var q = 0; q < lines.length; q++) {
        var graph = graphs[q];
        for (var i = 0; i < lines[q].length; i++) {
            var path = document.createElementNS("http://www.w3.org/2000/svg","path");
            var color = settings.colors[i % settings.colors.length];
            var id = q + "," + i;
            path.setAttribute("d", lines[q][i]);
            path.setAttribute("fill", "transparent");
            path.setAttribute("stroke", color);
            path.id = id + "path";
            document.getElementById(id + "per").style.color = color;
            document.getElementById(id).onclick = function () {
                toggle(this.id);
            }
            graph.appendChild(path);
        }
    }
}
