import { LightningElement, api } from 'lwc';

export default class ClassBookingConfirmation extends LightningElement {
    @api memberName = '';
    @api className = '';
    @api classDateTime;

    get firstName() {
        if (!this.memberName) {
            return 'there';
        }
        return this.memberName.trim().split(' ')[0];
    }

    get formattedDateTime() {
        if (!this.classDateTime) {
            return '';
        }
        const d = new Date(this.classDateTime);
        return d.toLocaleString(undefined, {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }
}
