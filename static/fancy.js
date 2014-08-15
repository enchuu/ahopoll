function toggle(filters, votes, counts) {
    this.state = (this.state + 1) % 3;
    if (this.state == 1) {
        this.style.color = "blue";
        filters[this.id] = true;
    }
    else if (this.state == 2) {
        this.style.color = "red";
        filters[this.id] = false;
    }
    else {
        this.style.color = "black";
        delete filters[this.id];
    }
    refresh(filters, votes, counts, true);
}

function setup(votes) {
    var entrees = document.getElementsByClassName("entree");
    var counts = [];
    var filters = {};
    for (var i = 0; i < entrees.length; i++) {
        (function (entree) {
            entree.state = 0;
            entree.onclick = function () { toggle.call(entree, filters, votes, counts) };
            var qo = entree.id.split(",");
            var q = qo[0],
                o = qo[1];
            if (!counts[q]) {
                counts[q] = [];
            }
            counts[q][o] = 0;
        })(entrees[i]);
    }
    return [counts, filters];
}

function makeFilters(filters) {
    function filterVotes(vote) {
        var keys = Object.keys(filters);
        for (var i = 0; i < keys.length; i++) {
            var filter = filters[keys[i]];
            var qo = keys[i].split(",");
            var q = qo[0],
                o = qo[1];
            var inVote = vote.vote[q].indexOf(o) != -1;
            if (inVote ? !filter : filter) {
                return false;
            }
        }
        return true;
    }
    return filterVotes;
}
        
function clearCounts(counts) {
    for (var i = 0; i < counts.length; i++) {
        for (var j = 0; j < counts[i].length; j++) {
            counts[i][j] = 0;
        }
    }
    return counts;
}

function tallyVotes(votes, counts) {
    for (var i = 0; i < votes.length; i++) {
        var vote = votes[i].vote;
        for (var j = 0, keys = Object.keys(vote); j < keys.length; j++) {
            var q = vote[keys[j]];
            for (var k = 0; k < q.length; k++) {
                counts[j][q[k]]++;
            }
        }
    }
    return counts;
}

function refresh(filters, votes, counts, overall) {
    voteFilter = makeFilters(filters);
    var filteredVotes = votes.filter(voteFilter);
    var total = overall ? votes.length : filteredVotes.length;
    var total = total ? total : 1;
    var counts = tallyVotes(filteredVotes, clearCounts(counts));
    for (var i = 0; i < counts.length; i++) {
        for (var j = 0; j < counts[i].length; j++) {
            var percentage = counts[i][j] / total * 100;
            var px = counts[i][j] / total * 580;
            var id = i + "," + j;
            document.getElementById(id + "bar").style.width = px + "px";
            document.getElementById(id + "per").innerHTML = parseInt(percentage) + "%";
            document.getElementById(id + "votes").innerHTML = counts[i][j];
        }
    }
    document.getElementById("selected_votes").innerHTML = "" + filteredVotes.length;
}
            

window.onload = function () {
    var stuff = setup(votes);
}
