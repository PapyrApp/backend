import { User } from "./user";

export interface PDFDocument {
    _id: string,
    owner: User;
    title: string;
    description?: string;
    status: DocumentStatus;
    collaborators?: User[];
    can_share: boolean;
    share_token: string;
    created_at: Date;
    updated_at: Date;
}

export interface CreatePDFDocument {
    title: string;
    description?: string;
}

export interface UpdatePDFDocument {
    title: string;
    description?: string;
    status: DocumentStatus;
    can_share: boolean;
}

enum DocumentStatus {
  Active = "ACTIVE",
  Archived = "ARCHIVED",
}