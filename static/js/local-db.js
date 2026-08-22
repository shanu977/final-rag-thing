/**
 * IndexedDB Local Storage for Chat History
 * Database: nexuss_chat_db
 * Version: 1
 * Object Stores: chat_sessions, chat_messages, settings
 */

const DB_NAME = 'nexuss_chat_db';
const DB_VERSION = 1;
const STORES = {
    SESSIONS: 'chat_sessions',
    MESSAGES: 'chat_messages',
    SETTINGS: 'settings'
};

class LocalDB {
    constructor() {
        this.db = null;
        this.initPromise = this.init();
    }

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => {
                console.error('IndexedDB open error:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                console.log('IndexedDB initialized successfully');
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                if (!db.objectStoreNames.contains(STORES.SESSIONS)) {
                    const sessionStore = db.createObjectStore(STORES.SESSIONS, { keyPath: 'id' });
                    sessionStore.createIndex('user_id', 'user_id', { unique: false });
                    sessionStore.createIndex('updated_at', 'updated_at', { unique: false });
                }

                if (!db.objectStoreNames.contains(STORES.MESSAGES)) {
                    const messageStore = db.createObjectStore(STORES.MESSAGES, { keyPath: 'id' });
                    messageStore.createIndex('session_id', 'session_id', { unique: false });
                    messageStore.createIndex('created_at', 'created_at', { unique: false });
                }

                if (!db.objectStoreNames.contains(STORES.SETTINGS)) {
                    db.createObjectStore(STORES.SETTINGS, { keyPath: 'key' });
                }
            };
        });
    }

    async ensureReady() {
        if (!this.db) {
            await this.initPromise;
        }
        return this.db;
    }

    // Generic methods
    async _transaction(storeName, mode, callback) {
        await this.ensureReady();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, mode);
            const store = transaction.objectStore(storeName);

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error);

            callback(store);
        });
    }

    async _get(storeName, key) {
        await this.ensureReady();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(key);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async _getAll(storeName, indexName = null, indexValue = null) {
        await this.ensureReady();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);

            let request;
            if (indexName && indexValue !== null) {
                const index = store.index(indexName);
                request = index.getAll(indexValue);
            } else {
                request = store.getAll();
            }

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async _put(storeName, data) {
        await this.ensureReady();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.put(data);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async _delete(storeName, key) {
        await this.ensureReady();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.delete(key);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async _clear(storeName) {
        await this.ensureReady();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    // Session methods
    async createSession(userId, title = 'New Chat') {
        const now = new Date().toISOString();
        const session = {
            id: crypto.randomUUID(),
            user_id: userId || 'anonymous',
            title: title,
            created_at: now,
            updated_at: now
        };
        await this._put(STORES.SESSIONS, session);
        return session;
    }

    async getSession(sessionId) {
        return this._get(STORES.SESSIONS, sessionId);
    }

    async getAllSessions(userId) {
        const sessions = await this._getAll(STORES.SESSIONS, 'user_id', userId);
        return sessions.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
    }

    async updateSession(sessionId, updates) {
        const session = await this.getSession(sessionId);
        if (!session) return null;

        const updated = { ...session, ...updates, updated_at: new Date().toISOString() };
        await this._put(STORES.SESSIONS, updated);
        return updated;
    }

    async deleteSession(sessionId) {
        // Delete session and all its messages in a transaction
        await this.ensureReady();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORES.SESSIONS, STORES.MESSAGES], 'readwrite');
            const sessionStore = transaction.objectStore(STORES.SESSIONS);
            const messageStore = transaction.objectStore(STORES.MESSAGES);

            // Delete session
            sessionStore.delete(sessionId);

            // Delete all messages for this session
            const messageIndex = messageStore.index('session_id');
            const messageRequest = messageIndex.getAllKeys(sessionId);
            messageRequest.onsuccess = () => {
                messageRequest.result.forEach(key => messageStore.delete(key));
            };

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        });
    }

    // Message methods
    async addMessage(sessionId, role, content, sources = []) {
        const message = {
            id: crypto.randomUUID(),
            session_id: sessionId,
            role: role, // 'user' or 'assistant'
            content: content,
            sources: sources,
            created_at: new Date().toISOString()
        };
        await this._put(STORES.MESSAGES, message);

        // Update session's updated_at
        await this.updateSession(sessionId, {});

        return message;
    }

    async getMessages(sessionId) {
        const messages = await this._getAll(STORES.MESSAGES, 'session_id', sessionId);
        return messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }

    async deleteMessages(sessionId) {
        await this.ensureReady();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(STORES.MESSAGES, 'readwrite');
            const store = transaction.objectStore(STORES.MESSAGES);
            const index = store.index('session_id');
            const request = index.getAllKeys(sessionId);

            request.onsuccess = () => {
                request.result.forEach(key => store.delete(key));
            };

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        });
    }

    // Settings methods
    async setSetting(key, value) {
        await this._put(STORES.SETTINGS, { key, value });
    }

    async getSetting(key) {
        const result = await this._get(STORES.SETTINGS, key);
        return result ? result.value : null;
    }

    // Export all data (for backup)
    async exportAll(userId) {
        const sessions = await this.getAllSessions(userId);
        const allMessages = {};

        for (const session of sessions) {
            allMessages[session.id] = await this.getMessages(session.id);
        }

        return {
            exportDate: new Date().toISOString(),
            userId: userId,
            sessions: sessions,
            messages: allMessages
        };
    }

    // Clear all data for a user
    async clearUserData(userId) {
        const sessions = await this.getAllSessions(userId);
        for (const session of sessions) {
            await this.deleteSession(session.id);
        }
    }
}

// Export singleton instance
const localDB = new LocalDB();
export default localDB;