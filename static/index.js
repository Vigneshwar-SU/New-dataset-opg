function goHome(){

let upload = document.getElementById("uploadBox");

upload.style.display="block";
upload.classList.add("home-center-box");

document.getElementById("resultBox").style.display="none";
document.getElementById("aboutSection").style.display="none";
document.getElementById("modelSection").style.display="none";

}


function goUpload(){

let upload = document.getElementById("uploadBox");
upload.classList.remove("home-center-box");

document.getElementById("uploadBox").style.display="block";
document.getElementById("resultBox").style.display="block";

/* Hide About and Model */
document.getElementById("aboutSection").style.display="none";
document.getElementById("modelSection").style.display="none";

upload.scrollIntoView({behavior:"smooth"});

/* open file selector */
document.querySelector('input[type="file"]').click();

}

function showAbout(){

let upload = document.getElementById("uploadBox");
upload.classList.remove("home-center-box");

document.getElementById("uploadBox").style.display="block";
document.getElementById("resultBox").style.display="block";
document.getElementById("aboutSection").style.display="block";
document.getElementById("modelSection").style.display="none";

}

function showModel(){

let upload = document.getElementById("uploadBox");
upload.classList.remove("home-center-box");

document.getElementById("uploadBox").style.display="block";
document.getElementById("resultBox").style.display="block";
document.getElementById("aboutSection").style.display="none";
document.getElementById("modelSection").style.display="block";

}

