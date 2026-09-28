import { LightningElement, api, wire } from 'lwc';
import { FlowAttributeChangeEvent } from 'lightning/flowSupport';
import getUpcomingClasses from '@salesforce/apex/ClassBookingController.getUpcomingClasses';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default class ClassBookingForm extends LightningElement {
    @api memberName = '';
    @api memberEmail = '';
    @api selectedClassId = '';

    classes = [];
    isLoading = true;
    loadError = false;

    @wire(getUpcomingClasses)
    wiredClasses({ data, error }) {
        this.isLoading = false;
        if (data) {
            this.loadError = false;
            this.classes = data.map((c) => this.decorateClass(c));
        } else if (error) {
            this.loadError = true;
        }
    }

    decorateClass(c) {
        return {
            ...c,
            formattedDate: this.formatDateTime(c.startDateTime),
            cardClass: this.computeCardClass(c.id, c.isFull),
            seatsLabel: c.isFull
                ? 'Fully booked'
                : `${c.seatsAvailable} ${c.seatsAvailable === 1 ? 'seat' : 'seats'} left`
        };
    }

    formatDateTime(value) {
        if (!value) {
            return '';
        }
        const d = new Date(value);
        return d.toLocaleString(undefined, {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }

    computeCardClass(id, isFull) {
        let cls = 'class-card';
        if (isFull) {
            cls += ' class-card_full';
        }
        if (id === this.selectedClassId) {
            cls += ' class-card_selected';
        }
        return cls;
    }

    get hasClasses() {
        return this.classes && this.classes.length > 0;
    }

    handleNameChange(event) {
        this.memberName = event.target.value;
        this.dispatchAttributeChange('memberName', this.memberName);
    }

    handleEmailChange(event) {
        this.memberEmail = event.target.value;
        this.dispatchAttributeChange('memberEmail', this.memberEmail);
    }

    handleSelectClass(event) {
        const id = event.currentTarget.dataset.id;
        const clicked = this.classes.find((c) => c.id === id);
        if (!clicked || clicked.isFull) {
            return;
        }
        this.selectedClassId = id;
        this.classes = this.classes.map((c) => ({
            ...c,
            cardClass: this.computeCardClass(c.id, c.isFull)
        }));
        this.dispatchAttributeChange('selectedClassId', this.selectedClassId);
    }

    dispatchAttributeChange(attributeName, value) {
        this.dispatchEvent(new FlowAttributeChangeEvent(attributeName, value));
    }

    @api
    validate() {
        const messages = [];

        if (!this.memberName || !this.memberName.trim()) {
            messages.push('Please enter your full name.');
        }
        if (!this.memberEmail || !EMAIL_PATTERN.test(this.memberEmail)) {
            messages.push('Please enter a valid email address.');
        }
        if (!this.selectedClassId) {
            messages.push('Please select a class to book.');
        }

        if (messages.length > 0) {
            return [{ key: 'bookingFormValidation', errorMessage: messages.join(' ') }];
        }
        return [];
    }
}
