import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserPool,
  type CognitoUserSession,
} from "amazon-cognito-identity-js";
import type { Session } from "./types";

function config() {
  return {
    userPoolId:
      window.__WIKI_CONFIG__?.userPoolId ?? import.meta.env.VITE_COGNITO_USER_POOL_ID,
    clientId:
      window.__WIKI_CONFIG__?.userPoolClientId ??
      import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID,
  };
}

function pool(): CognitoUserPool {
  const { userPoolId, clientId } = config();
  if (!userPoolId || !clientId) {
    throw new Error("Cognito não configurado. Consulte .env.example e os outputs do CDK.");
  }
  return new CognitoUserPool({ UserPoolId: userPoolId, ClientId: clientId });
}

function toSession(session: CognitoUserSession): Session {
  const payload = session.getIdToken().decodePayload() as { email?: string };
  return {
    email: payload.email ?? "usuário autenticado",
    idToken: session.getIdToken().getJwtToken(),
  };
}

export function signIn(email: string, password: string): Promise<Session> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: pool() });
    user.authenticateUser(new AuthenticationDetails({ Username: email, Password: password }), {
      onSuccess: (session) => resolve(toSession(session)),
      onFailure: (error: unknown) =>
        reject(error instanceof Error ? error : new Error("Falha de autenticação.")),
      newPasswordRequired: () => reject(new Error("Uma nova senha deve ser definida no Cognito.")),
    });
  });
}

export function restoreSession(): Promise<Session | null> {
  const { userPoolId, clientId } = config();
  if (!userPoolId || !clientId) return Promise.resolve(null);
  const user = pool().getCurrentUser();
  if (!user) return Promise.resolve(null);
  return new Promise((resolve) => {
    user.getSession((error: Error | null, session: CognitoUserSession | null) => {
      if (error || !session?.isValid()) resolve(null);
      else resolve(toSession(session));
    });
  });
}

export function signOut(): void {
  pool().getCurrentUser()?.signOut();
}
