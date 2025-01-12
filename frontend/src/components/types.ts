export type NotificationType = "success" | "info" | "warning" | "error";

export interface IMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  user_id?: string;
  timestamp?: string;
  personalize?: boolean;
  ra?: string;
  session_id?: string;
  agency_id?: string;
}

export interface IStatus {
  message: string;
  status: boolean;
  data?: any;
}

export interface IChatMessage {
  text: string;
  sender: "user" | "assistant";
  metadata?: any;
  id?: string;
}

export interface IAgentConfig {
  name: string;
  system_message: string | "";
  model: string;
  code_execution_config?: boolean | string | { [key: string]: any } | null;
  temperature: float | 0.0;
}

export interface IAgentFlowSpec {
  config: IAgentConfig;
  timestamp?: string;
  id?: string;
  skills?: Array<ISkill>;
  description?: string;
  user_id?: string;
}

export interface IFlowConfig {
  name: string;
  description: string;
  flows: Array<{
    sender: IAgentFlowSpec;
    receiver?: IAgentFlowSpec;
  }>;
  type: "twoagents" | "groupchat";
  timestamp?: string;
  id?: string;
  user_id?: string;
}

export interface IMetadataFile {
  name: string;
  path: string;
  extension: string;
  content: string;
  type: string;
}

export interface IChatSession {
  id: string;
  user_id: string;
  timestamp: string;
  flow_config: IFlowConfig;
  name: string;
}

export interface ISkill {
  title: string;
  file_name?: string;
  content: string;
  id?: string;
  timestamp?: string;
  description?: string;
  user_id?: string;
}
