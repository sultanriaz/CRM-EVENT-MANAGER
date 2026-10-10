import { LightningElement, api } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';
import getPage from '@salesforce/apex/EnterpriseWorkspaceController.getPage';

const CONFIG = {
    Contact: {
        title: 'Students & Contacts', subtitle: 'Search people and open complete Salesforce contact records.', icon: 'standard:contact',
        fields: [
            ['Name', 'Contact', 'text'], ['Email', 'Email', 'email'], ['Phone', 'Phone', 'phone'],
            ['Title', 'Title', 'text'], ['Account.Name', 'Account', 'text']
        ]
    },
    Society__c: {
        title: 'Societies', subtitle: 'Manage active societies, categories, advisors, and engagement totals.', icon: 'standard:groups',
        fields: [
            ['Name', 'Society', 'text'], ['Category__c', 'Category', 'text'], ['Active__c', 'Active', 'boolean'],
            ['Faculty_Advisor_Email__c', 'Advisor Email', 'email'], ['Completed_Events__c', 'Completed Events', 'number'],
            ['Total_Attendees__c', 'Total Attendees', 'number']
        ],
        filter: ['Active__c', 'Status', [['true', 'Active'], ['false', 'Inactive']]]
    },
    Event__c: {
        title: 'Events', subtitle: 'Monitor schedules, venues, capacity, availability, and registration status.', icon: 'standard:event',
        fields: [
            ['Name', 'Event', 'text'], ['Society__r.Name', 'Society', 'text'], ['Start_Date_Time__c', 'Starts', 'date'],
            ['Venue__c', 'Venue', 'text'], ['Status__c', 'Status', 'text'], ['Capacity__c', 'Capacity', 'number'],
            ['Seats_Remaining__c', 'Seats Left', 'number'], ['Fill_Status__c', 'Fill Status', 'text'], ['Ticket_Price__c', 'Ticket Price', 'currency']
        ],
        filter: ['Status__c', 'Status', [['Planned', 'Planned'], ['Open for Registration', 'Open for Registration'], ['Full', 'Full'], ['Completed', 'Completed'], ['Cancelled', 'Cancelled']]]
    },
    Registration__c: {
        title: 'Registrations', subtitle: 'Review students, events, departments, dates, and attendance.', icon: 'standard:orders',
        fields: [
            ['Name', 'Registration', 'text'], ['Student__r.Name', 'Student', 'text'], ['Event__r.Name', 'Event', 'text'],
            ['Student_Department__c', 'Department', 'text'], ['Registration_Date__c', 'Registered', 'date'], ['Attended__c', 'Attended', 'boolean']
        ],
        filter: ['Attended__c', 'Attendance', [['true', 'Attended'], ['false', 'Not attended']]]
    },
    Class__c: {
        title: 'Classes', subtitle: 'Browse the current class schedule, trainers, and available capacity.', icon: 'standard:service_appointment',
        fields: [['Name', 'Class', 'text'], ['Trainer__r.Name', 'Trainer', 'text'], ['Start_Date_Time__c', 'Starts', 'date'], ['Capacity__c', 'Capacity', 'number'], ['Description__c', 'Description', 'text']]
    },
    Trainer__c: {
        title: 'Trainers', subtitle: 'Find trainers by specialty and review their experience.', icon: 'standard:people',
        fields: [['Name', 'Trainer', 'text'], ['Specialty__c', 'Specialty', 'text'], ['Years_of_Experience__c', 'Experience', 'number'], ['Biography__c', 'Biography', 'text']]
    },
    Class_Booking__c: {
        title: 'Class Bookings', subtitle: 'Track members, classes, and booking lifecycle status.', icon: 'standard:product_request_line_item',
        fields: [['Name', 'Booking', 'text'], ['Contact__r.Name', 'Member', 'text'], ['Class__r.Name', 'Class', 'text'], ['Status__c', 'Status', 'text']],
        filter: ['Status__c', 'Status', [['Booked', 'Booked'], ['Attended', 'Attended'], ['Cancelled', 'Cancelled'], ['No-Show', 'No-Show']]]
    },
    Payment__c: {
        title: 'Payments', subtitle: 'Review member payments and transaction status.', icon: 'standard:currency',
        fields: [['Name', 'Payment', 'text'], ['Member__r.Name', 'Member', 'text'], ['Class_Booking__r.Name', 'Booking', 'text'], ['Amount__c', 'Amount', 'currency'], ['Payment_Date__c', 'Date', 'date'], ['Status__c', 'Status', 'text']],
        filter: ['Status__c', 'Status', [['Pending', 'Pending'], ['Completed', 'Completed'], ['Failed', 'Failed'], ['Refunded', 'Refunded']]]
    },
    Loyalty_Points__c: {
        title: 'Loyalty & Rewards', subtitle: 'Understand points activity and member reward tiers.', icon: 'standard:reward',
        fields: [['Name', 'Activity', 'text'], ['Contact__r.Name', 'Member', 'text'], ['Points_Earned__c', 'Points Earned', 'number'], ['Total_Points__c', 'Total Points', 'number'], ['Tier__c', 'Tier', 'text'], ['Loyalty_Date__c', 'Date', 'date']],
        filter: ['Tier__c', 'Tier', [['Bronze', 'Bronze'], ['Silver', 'Silver'], ['Gold', 'Gold'], ['Platinum', 'Platinum']]]
    },
    Lab_Student__c: {
        title: 'Lab Students', subtitle: 'Search student records and review class and demographic details.', icon: 'standard:person_account',
        fields: [['Name', 'Student', 'text'], ['Student_ID__c', 'Student ID', 'text'], ['Class__r.Name', 'Class', 'text'], ['Age__c', 'Age', 'number'], ['Gender__c', 'Gender', 'text'], ['City__c', 'City', 'text'], ['Country__c', 'Country', 'text']],
        filter: ['Gender__c', 'Gender', [['Male', 'Male'], ['Female', 'Female'], ['Other', 'Other']]]
    },
    Lab_Class__c: {
        title: 'Lab Classes', subtitle: 'Review lab class definitions and maximum strength.', icon: 'standard:education',
        fields: [['Name', 'Record', 'text'], ['Class_Name__c', 'Class', 'text'], ['Max_Strength__c', 'Maximum Strength', 'number']]
    }
};

const PAGE_SIZE_OPTIONS = [
    { label: '10 per page', value: '10' },
    { label: '20 per page', value: '20' },
    { label: '50 per page', value: '50' }
];

export default class EnterpriseObjectWorkspace extends NavigationMixin(LightningElement) {
    @api objectApiName;
    rows = [];
    visibleFields = [];
    totalRecords = 0;
    pageNumber = 1;
    pageSize = 20;
    draftSearch = '';
    searchTerm = '';
    filterValue = '';
    sortBy = 'Name';
    sortDirection = 'asc';
    loading = true;
    errorMessage;
    canCreate = false;
    canEdit = false;
    theme = 'light';

    connectedCallback() {
        try {
            this.theme = window.localStorage.getItem('enterpriseWorkspaceTheme') || 'light';
        } catch (error) {
            this.theme = 'light';
        }
        this.loadRecords();
    }

    get config() {
        return CONFIG[this.objectApiName] || { title: 'Records', subtitle: 'Secure Salesforce records.', icon: 'standard:record', fields: [] };
    }

    get title() { return this.config.title; }
    get subtitle() { return this.config.subtitle; }
    get iconName() { return this.config.icon; }
    get shellClass() { return `workspace-shell theme-${this.theme}`; }
    get themeIcon() { return this.theme === 'dark' ? 'utility:sun' : 'utility:moon'; }
    get themeLabel() { return this.theme === 'dark' ? 'Use light theme' : 'Use dark theme'; }
    get hasFilter() { return Boolean(this.config.filter); }
    get filterLabel() { return this.config.filter ? this.config.filter[1] : 'Filter'; }
    get filterField() { return this.config.filter ? this.config.filter[0] : ''; }
    get filterOptions() {
        const configured = this.config.filter ? this.config.filter[2] : [];
        return [{ label: `All ${this.filterLabel.toLowerCase()} values`, value: '' }, ...configured.map(([value, label]) => ({ value, label }))];
    }
    get pageSizeOptions() { return PAGE_SIZE_OPTIONS; }
    get pageSizeValue() { return String(this.pageSize); }
    get hasRows() { return this.rows.length > 0; }
    get showEmpty() { return !this.loading && !this.errorMessage && !this.hasRows; }
    get showTable() { return !this.errorMessage && this.hasRows; }
    get totalPages() { return Math.max(1, Math.ceil(this.totalRecords / this.pageSize)); }
    get pageSummary() { return `Page ${this.pageNumber} of ${this.totalPages}`; }
    get recordSummary() { return `${this.totalRecords} record${this.totalRecords === 1 ? '' : 's'}`; }
    get sortedByKey() {
        if (this.sortBy === 'Name') return 'recordUrl';
        return this.sortBy.replaceAll('.', '_');
    }
    get disablePrevious() { return this.loading || this.pageNumber <= 1; }
    get disableNext() { return this.loading || this.pageNumber >= this.totalPages; }

    get columns() {
        const visible = new Set(this.visibleFields);
        const dataColumns = this.config.fields
            .filter(([api]) => visible.has(api))
            .map(([api, label, type]) => {
                const key = api.replaceAll('.', '_');
                if (api === 'Name') {
                    return {
                        label,
                        fieldName: 'recordUrl',
                        type: 'url',
                        sortable: true,
                        typeAttributes: { label: { fieldName: key }, target: '_self' },
                        sortApi: api
                    };
                }
                const column = { label, fieldName: key, type, sortable: true, sortApi: api };
                if (type === 'date') {
                    column.typeAttributes = { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' };
                }
                if (type === 'currency') {
                    column.typeAttributes = { minimumFractionDigits: 2, maximumFractionDigits: 2 };
                }
                return column;
            });
        dataColumns.push({
            type: 'action',
            typeAttributes: {
                rowActions: this.canEdit
                    ? [{ label: 'View', name: 'view' }, { label: 'Edit', name: 'edit' }]
                    : [{ label: 'View', name: 'view' }]
            }
        });
        return dataColumns;
    }

    async loadRecords() {
        if (!this.objectApiName) {
            this.loading = false;
            this.errorMessage = 'The object context is unavailable.';
            return;
        }
        this.loading = true;
        this.errorMessage = undefined;
        try {
            const page = await getPage({
                objectApiName: this.objectApiName,
                searchTerm: this.searchTerm,
                filterField: this.filterField,
                filterValue: this.filterValue,
                sortBy: this.sortBy,
                sortDirection: this.sortDirection,
                pageSize: this.pageSize,
                pageNumber: this.pageNumber
            });
            this.rows = page.rows || [];
            this.visibleFields = page.visibleFields || [];
            this.totalRecords = page.totalRecords || 0;
            this.pageNumber = page.pageNumber || 1;
            this.pageSize = page.pageSize || 20;
            this.canCreate = Boolean(page.createable);
            this.canEdit = Boolean(page.updateable);
        } catch (error) {
            this.rows = [];
            this.errorMessage = this.normalizeError(error);
        } finally {
            this.loading = false;
        }
    }

    handleSearchInput(event) { this.draftSearch = event.target.value; }
    handleSearch() { this.searchTerm = this.draftSearch.trim(); this.pageNumber = 1; this.loadRecords(); }
    handleClear() { this.draftSearch = ''; this.searchTerm = ''; this.filterValue = ''; this.pageNumber = 1; this.loadRecords(); }
    handleFilter(event) { this.filterValue = event.detail.value; this.pageNumber = 1; this.loadRecords(); }
    handlePageSize(event) { this.pageSize = Number(event.detail.value); this.pageNumber = 1; this.loadRecords(); }
    handlePrevious() { if (this.pageNumber > 1) { this.pageNumber -= 1; this.loadRecords(); } }
    handleNext() { if (this.pageNumber < this.totalPages) { this.pageNumber += 1; this.loadRecords(); } }
    handleRefresh() { this.loadRecords(); }

    handleSort(event) {
        const selected = this.columns.find((column) => column.fieldName === event.detail.fieldName);
        this.sortBy = selected?.sortApi || 'Name';
        this.sortDirection = event.detail.sortDirection;
        this.pageNumber = 1;
        this.loadRecords();
    }

    handleRowAction(event) {
        const action = event.detail.action.name;
        const recordId = event.detail.row.Id;
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: { recordId, objectApiName: this.objectApiName, actionName: action }
        });
    }

    handleNew() {
        this[NavigationMixin.Navigate]({
            type: 'standard__objectPage',
            attributes: { objectApiName: this.objectApiName, actionName: 'new' }
        });
    }

    toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        try { window.localStorage.setItem('enterpriseWorkspaceTheme', this.theme); } catch (error) { /* preference storage is optional */ }
    }

    normalizeError(error) {
        const body = error?.body;
        if (Array.isArray(body)) return body.map((item) => item.message).join(', ');
        return body?.message || error?.message || 'The records could not be loaded.';
    }
}
