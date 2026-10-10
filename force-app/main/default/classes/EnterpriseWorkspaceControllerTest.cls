@IsTest
private class EnterpriseWorkspaceControllerTest {
    @IsTest
    static void returnsFilteredPagedContacts() {
        insert new List<Contact>{
            new Contact(LastName = 'Workspace Alpha', Email = 'alpha.workspace@example.edu', Phone = '0321-1234567'),
            new Contact(LastName = 'Workspace Beta', Email = 'beta.workspace@example.edu', Phone = '0322-1234567')
        };

        Test.startTest();
        EnterpriseWorkspaceController.WorkspacePage page = EnterpriseWorkspaceController.getPage(
            'Contact', 'Workspace', 'Email', 'alpha.workspace@example.edu', 'Name', 'ASC', 20, 1
        );
        EnterpriseWorkspaceController.WorkspacePage fallbackSort = EnterpriseWorkspaceController.getPage(
            'Contact', 'Workspace', null, null, 'Untrusted_Field__c', 'SIDEWAYS', 5, 1
        );
        Test.stopTest();

        System.assertEquals(1, page.totalRecords);
        System.assertEquals(1, page.rows.size());
        System.assertEquals('alpha.workspace@example.edu', page.rows[0].get('Email'));
        System.assertEquals(2, fallbackSort.totalRecords);
        System.assert(fallbackSort.visibleFields.contains('Name'));
        System.assertNotEquals(null, fallbackSort.rows[0].get('recordUrl'));
    }

    @IsTest
    static void rejectsUnconfiguredObjects() {
        try {
            EnterpriseWorkspaceController.getPage('Account', null, null, null, null, null, 20, 1);
            System.assert(false, 'An unsupported object must be rejected.');
        } catch (AuraHandledException expected) {
            System.assert(true);
        }
    }
}
