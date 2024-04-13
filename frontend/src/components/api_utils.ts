import { IStatus } from "./types";
import { fetchJSON, getServerUrl } from "./api_utils";
import { message } from "antd";
import { auth } from '../firebase/firebase-config';
import { store } from "../store";
import { RefreshToken } from "../store/actions/usersActions";

export const getServerUrl = () => {
  return process.env.GATSBY_API_URL || "/v1/api";
};

export function checkAndRefreshToken() {
  return new Promise((resolve) => {
    const userState = store.getState().user;

    if (userState && userState.expiresIn) {
      if (Date.now() >= userState.expiresIn) {
        // FIXME: sometimes auth is not defined
        const user = auth.currentUser;
        if (user) {
          user.getIdToken(true).then((newToken) => {
            const newExpiresIn = Date.now() + (55 * 60) * 1000; // 55 minutes from now
            store.dispatch(
              RefreshToken({
                token: newToken,
                expiresIn: newExpiresIn,
              })
            );
            resolve(true);
          }).catch(error => {
            console.error("Error refreshing token:", error);
            message.error("Error refreshing token. Please login again.");
            resolve(false);
          });
        } else {
          console.error("User not logged in.");
          resolve(false);
        }
      } else {
        resolve(true); // Token is still valid
      }
    } else {
      console.error("User state not populated yet.");
      resolve(false);
    }
  });
}

export function fetchJSON(
  url: string | URL,
  payload: any = {},
  onSuccess: (data: any) => void,
  onError: (error: IStatus) => void
) {
  checkAndRefreshToken().then((canProceed) => {
    if (!canProceed) {
      onError({
        status: false,
        message: "Refresh the page or login again.",
      });
      return;
    }

    const accessToken = store.getState().user.accessToken;

    const fetchOptions = {
      method: payload.method,
      headers: { ...payload.headers, Authorization: `Bearer ${accessToken}` },
    };
    if (payload.body) {
      fetchOptions.body = payload.body;
    }

    fetch(url, fetchOptions)
    .then(function (response) {
      if (response.status !== 200) {
        console.log(
          "Looks like there was a problem. Status Code: " + response.status,
          response
        );
        response.json().then(function (data) {
          console.log("Error data", data);
        });
        onError({
          status: false,
          message: "Connection error " + response.status + " " + response.statusText,
        });
        return;
      }
      response.json().then(function (data) {
        onSuccess(data);
      });
    })
    .catch(function (err) {
      console.log("Fetch Error :-S", err);
      onError({
        status: false,
        message: `There was an error connecting to server. (${err}) `,
      });
    });
  });
}

export const fetchMessages = async (sessionId: string, after: string | null = null) => {
  const serverUrl = getServerUrl();
  const fetchMessagesUrl = `${serverUrl}/message/list?session_id=${sessionId}${after ? `&after=${after}` : ""}`;

  const payload = {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  };

  try {
    const data = await fetchJSON(fetchMessagesUrl, payload);
    if (data && data.status) {
      return data.data;
    } else {
      throw new Error(data.message);
    }
  } catch (error) {
    console.error("Error fetching messages:", error);
    throw error;
  }
};


export const fetchVersion = () => {
  const versionUrl = getServerUrl() + "/version";
  return fetch(versionUrl)
    .then((response) => response.json())
    .then((data) => {
      return data;
    })
    .catch((error) => {
      console.error("Error:", error);
      return null;
    });
};
