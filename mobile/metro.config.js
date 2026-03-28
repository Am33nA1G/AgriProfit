// metro.config.js
// Fixes axios v1.x importing Node's `crypto` module — redirect to browser build.
// See: https://docs.expo.dev/workflow/using-libraries/#using-third-party-libraries

const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Redirect axios to its browser-compatible build (no Node built-ins)
const originalResolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
    if (moduleName === 'axios') {
        return {
            filePath: require.resolve('axios/dist/browser/axios.cjs'),
            type: 'sourceFile',
        };
    }
    if (originalResolveRequest) {
        return originalResolveRequest(context, moduleName, platform);
    }
    return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
