## 🚀 Running UI in Dev Mode

To run the UI in development mode (make changes and see them reflected in the browser with hot reloading), follow these steps:

1. `npm install` - Installs necessary dependencies.
2. `yarn start` - Starts the development server.
3. `yarn build` - Builds the app for production (optional).

## 🛠️ Codebase Overview

Our frontend codebase is structured around React components and utilities designed to support dynamic and scalable web application development. Here's a quick overview:

### Core Components
- **Components**: Located in `frontend/src/components`, includes everything from layout wrappers to small atomic components.
- **Views**: Components specific to application views are in `frontend/src/components/views`, categorized under directories like `builder`, `test` and `deploy`.
- **Utilities**: Helper functions and utilities are in `frontend/src/components/utils`.

### Pages and Routing
- **Pages**: Entry points for different routes are in `frontend/src/pages`.
- **Routing**: Integrated with Gatsby for seamless page transitions and dynamic routing.

### State Management
- **Redux**: Used for state management across the application, setup can be found in `frontend/src/store`.

### API Integration
- **API Utilities**: Functions to interact with the backend API are centralized in `frontend/src/components/api_utils.tsx`.

### Styles and UI
- **Ant Design**: Leveraged for UI components.
- **TailwindCSS**: For custom styling needs.

### Development Tools
- **Firebase**: Utilized for authentication.
- **Redux Persist**: For persistent state management.

For a detailed view of each component and utility, refer to the respective files in the source directory.

## 🎨 Design Elements

### Gatsby
- The app is built with **Gatsby**, providing fast setup and rich configurations. Learn more about setting up a Gatsby app [here](https://www.gatsbyjs.com/docs/quick-start/).
- Key files include `gatsby-config.js`, `gatsby-node.js`, `gatsby-browser.js`, and `gatsby-ssr.js`.

### TailwindCSS
- Styling is managed with **TailwindCSS**. A guide to integrating TailwindCSS with Gatsby is available [here](https://tailwindcss.com/docs/guides/gatsby).

## 🌐 Modifying the UI, Adding Pages

To add new pages:
1. Create a new folder in `src/pages`.
2. Add an `index.tsx` file as the entry point. Use the content style from `src/pages/index.tsx` as a template.

## 🔗 Connecting to the Backend

The frontend expects the backend API to be available at `http://localhost:8000/api`.

## ⚙️ Setting Environment Variables for the UI

- Refer to `.env.default`.
- Copy this file and rename it to `.env.development`.
- Set the variable values, particularly `GATSBY_API_URL`, which should be `http://localhost:8000/api` for local development environments.
- Set up Firebase Authentication and Firestore and update the src/firebase/firebaseConfig.json file with your Firebase project configuration.
