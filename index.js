const dependencies = [
    {
        repo: 'null',
        lib: '',
        version: ''
    },
]

const download = async (url, filename) => {
    console.log(`downloading: ${filename}`);
    return await fetch(url)
        .then(response => response.blob())
        .then(blob => {
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            link.click();
        })
        .catch(console.error);
}

function timeout(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

const downloadDependencies = async (dependencies) => {
    for await (const value of dependencies) {
        console.log('value: ', value);
        let url, filename;
        if (value.repo) {
            url = `https://registry.yarnpkg.com/@${value.repo}/${value.lib}/-/${value.lib}-${value.version}.tgz`;
            filename = `${value.repo}-${value.lib}-${value.version}.tgz`;
        } else {
            url = `https://registry.yarnpkg.com/${value.lib}/-/${value.lib}-${value.version}.tgz`;
            filename = `${value.lib}-${value.version}.tgz`;
        }
        await download(url, filename);
        await timeout(5000)
    }
    console.log('FINISHED!!!!')
}

downloadDependencies(dependencies);