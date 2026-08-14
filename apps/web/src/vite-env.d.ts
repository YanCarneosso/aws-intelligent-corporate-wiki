/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_AWS_REGION?: string;
  readonly VITE_COGNITO_USER_POOL_ID?: string;
  readonly VITE_COGNITO_USER_POOL_CLIENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface Window {
  readonly __WIKI_CONFIG__?: {
    readonly apiUrl?: string;
    readonly awsRegion?: string;
    readonly userPoolId?: string;
    readonly userPoolClientId?: string;
  };
}
