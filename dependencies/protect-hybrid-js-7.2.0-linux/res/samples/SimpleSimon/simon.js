var passwordField;
var secretsArea;
var correctColor = "#e0ffe0";
var wrongColor = "#ffe0e0";
var secretsRevealed = false;

function startSimon()
{ 
	passwordField = document.getElementById("password");
	secretsArea = document.getElementById("secrets");
	passwordField.focus();
	checkPassword();
}

function checkPassword()
{
	var password = passwordField.value;
	if (password === "secret")
	{
		passwordField.style.backgroundColor = correctColor;
		revealSecrets();
	}
	else
	{
		passwordField.style.backgroundColor = wrongColor;
		if (secretsRevealed) clearSecrets();
	}
}

function revealSecrets()
{
	secretsArea.value = "Baked in credentials are never a good idea.";
	secretsRevealed = true;
}

function clearSecrets()
{
	secretsArea.value = "";
	secretsRevealed = false;
}
