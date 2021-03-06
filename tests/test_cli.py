import textwrap

from click.testing import CliRunner
import mock

from tests import BaseTestCase
from redash.utils.configuration import ConfigurationContainer
from redash.query_runner import query_runners
from redash.cli.data_sources import (edit, delete as delete_ds,
                                     list as list_ds, new, test)
from redash.cli.groups import (change_permissions, create as create_group,
                               list as list_group)
from redash.cli.organization import (list as list_org, set_google_apps_domains,
                                     show_google_apps_domains)
from redash.cli.users import (create as create_user, delete as delete_user,
                              grant_admin, invite, list as list_user, password)
from redash.models import DataSource, Group, Organization, User


class DataSourceCommandTests(BaseTestCase):
    def test_interactive_new(self):
        runner = CliRunner()
        pg_i = query_runners.keys().index('pg') + 1
        result = runner.invoke(
            new,
            input="test\n%s\n\n\nexample.com\n\ntestdb\n" % (pg_i,))
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(DataSource.select().count(), 1)
        ds = DataSource.select().first()
        self.assertEqual(ds.name, 'test')
        self.assertEqual(ds.type, 'pg')
        self.assertEqual(ds.options['dbname'], 'testdb')

    def test_options_new(self):
        runner = CliRunner()
        result = runner.invoke(
            new, ['test', '--options',
                  '{"host": "example.com", "dbname": "testdb"}',
                  '--type', 'pg'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(DataSource.select().count(), 1)
        ds = DataSource.select().first()
        self.assertEqual(ds.name, 'test')
        self.assertEqual(ds.type, 'pg')
        self.assertEqual(ds.options['host'], 'example.com')
        self.assertEqual(ds.options['dbname'], 'testdb')

    def test_bad_type_new(self):
        runner = CliRunner()
        result = runner.invoke(
            new, ['test', '--type', 'wrong'])
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('not supported', result.output)
        self.assertEqual(DataSource.select().count(), 0)

    def test_bad_options_new(self):
        runner = CliRunner()
        result = runner.invoke(
            new, ['test', '--options',
                  '{"host": 12345, "dbname": "testdb"}',
                  '--type', 'pg'])
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('invalid configuration', result.output)
        self.assertEqual(DataSource.select().count(), 0)

    def test_list(self):
        self.factory.create_data_source(
            name='test1', type='pg',
            options=ConfigurationContainer({"host": "example.com",
                                            "dbname": "testdb1"}))
        self.factory.create_data_source(
            name='test2', type='sqlite',
            options=ConfigurationContainer({"dbpath": "/tmp/test.db"}))
        runner = CliRunner()
        result = runner.invoke(list_ds)
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        expected_output = """
        Id: 1
        Name: test1
        Type: pg
        Options: {"dbname": "testdb1", "host": "example.com"}
        --------------------
        Id: 2
        Name: test2
        Type: sqlite
        Options: {"dbpath": "/tmp/test.db"}
        """
        self.assertMultiLineEqual(result.output,
                                  textwrap.dedent(expected_output).lstrip())

    def test_connection_test(self):
        self.factory.create_data_source(
            name='test1', type='sqlite',
            options=ConfigurationContainer({"dbpath": "/tmp/test.db"}))
        runner = CliRunner()
        result = runner.invoke(test, ['test1'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Success', result.output)

    def test_connection_bad_test(self):
        self.factory.create_data_source(
            name='test1', type='sqlite',
            options=ConfigurationContainer({"dbpath": __file__}))
        runner = CliRunner()
        result = runner.invoke(test, ['test1'])
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('Failure', result.output)

    def test_connection_delete(self):
        self.factory.create_data_source(
            name='test1', type='sqlite',
            options=ConfigurationContainer({"dbpath": "/tmp/test.db"}))
        runner = CliRunner()
        result = runner.invoke(delete_ds, ['test1'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Deleting', result.output)
        self.assertEqual(DataSource.select().count(), 0)

    def test_connection_bad_delete(self):
        self.factory.create_data_source(
            name='test1', type='sqlite',
            options=ConfigurationContainer({"dbpath": "/tmp/test.db"}))
        runner = CliRunner()
        result = runner.invoke(delete_ds, ['wrong'])
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Couldn't find", result.output)
        self.assertEqual(DataSource.select().count(), 1)

    def test_options_edit(self):
        self.factory.create_data_source(
            name='test1', type='sqlite',
            options=ConfigurationContainer({"dbpath": "/tmp/test.db"}))
        runner = CliRunner()
        result = runner.invoke(
            edit, ['test1', '--options',
                   '{"host": "example.com", "dbname": "testdb"}',
                   '--name', 'test2',
                   '--type', 'pg'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(DataSource.select().count(), 1)
        ds = DataSource.select().first()
        self.assertEqual(ds.name, 'test2')
        self.assertEqual(ds.type, 'pg')
        self.assertEqual(ds.options['host'], 'example.com')
        self.assertEqual(ds.options['dbname'], 'testdb')

    def test_bad_type_edit(self):
        self.factory.create_data_source(
            name='test1', type='sqlite',
            options=ConfigurationContainer({"dbpath": "/tmp/test.db"}))
        runner = CliRunner()
        result = runner.invoke(
            edit, ['test', '--type', 'wrong'])
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('not supported', result.output)
        ds = DataSource.select().first()
        self.assertEqual(ds.type, 'sqlite')

    def test_bad_options_edit(self):
        ds = self.factory.create_data_source(
            name='test1', type='sqlite',
            options=ConfigurationContainer({"dbpath": "/tmp/test.db"}))
        runner = CliRunner()
        result = runner.invoke(
            new, ['test', '--options',
                  '{"host": 12345, "dbname": "testdb"}',
                  '--type', 'pg'])
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('invalid configuration', result.output)
        ds = DataSource.select().first()
        self.assertEqual(ds.type, 'sqlite')
        self.assertEqual(ds.options._config, {"dbpath": "/tmp/test.db"})


class GroupCommandTests(BaseTestCase):

    def test_create(self):
        gcount = Group.select().count()
        perms = ['create_query', 'edit_query', 'view_query']
        runner = CliRunner()
        result = runner.invoke(
            create_group, ['test', '--permissions', ','.join(perms)])
        print result.output
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(Group.select().count(), gcount + 1)
        g = Group.select().order_by(Group.id.desc()).first()
        self.assertEqual(g.org, self.factory.org)
        self.assertEqual(g.permissions, perms)

    def test_change_permissions(self):
        g = self.factory.create_group(permissions=['list_dashboards'])
        g_id = g.id
        perms = ['create_query', 'edit_query', 'view_query']
        runner = CliRunner()
        result = runner.invoke(
            change_permissions, [str(g_id), '--permissions', ','.join(perms)])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        g = Group.select().where(Group.id == g_id).first()
        self.assertEqual(g.permissions, perms)

    def test_list(self):
        self.factory.create_group(name='test', permissions=['list_dashboards'])
        runner = CliRunner()
        result = runner.invoke(list_group, [])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        output = """
        Id: 1
        Name: admin
        Type: builtin
        Organization: default
        --------------------
        Id: 2
        Name: default
        Type: builtin
        Organization: default
        --------------------
        Id: 3
        Name: test
        Type: regular
        Organization: default
        """
        self.assertMultiLineEqual(result.output,
                                  textwrap.dedent(output).lstrip())


class OrganizationCommandTests(BaseTestCase):
    def test_set_google_apps_domains(self):
        domains = ['example.org', 'example.com']
        runner = CliRunner()
        result = runner.invoke(set_google_apps_domains, [','.join(domains)])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        o = Organization.select().where(
            Organization.id == self.factory.org.id).first()
        self.assertEqual(o.google_apps_domains, domains)

    def test_show_google_apps_domains(self):
        self.factory.org.settings[Organization.SETTING_GOOGLE_APPS_DOMAINS] = [
            'example.org', 'example.com']
        self.factory.org.save()
        runner = CliRunner()
        result = runner.invoke(show_google_apps_domains, [])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        output = """
        Current list of Google Apps domains: example.org, example.com
        """
        self.assertMultiLineEqual(result.output,
                                  textwrap.dedent(output).lstrip())

    def test_list(self):
        self.factory.create_org(name='test', slug='test_org')
        runner = CliRunner()
        result = runner.invoke(list_org, [])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        output = """
        Id: 1
        Name: Default
        Slug: default
        --------------------
        Id: 2
        Name: test
        Slug: test_org
        """
        self.assertMultiLineEqual(result.output,
                                  textwrap.dedent(output).lstrip())


class UserCommandTests(BaseTestCase):
    def test_create_basic(self):
        runner = CliRunner()
        result = runner.invoke(
            create_user, ['foobar@example.com', 'Fred Foobar'],
            input="password1\npassword1\n")
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        u = User.select().where(User.email == "foobar@example.com").first()
        self.assertEqual(u.name, "Fred Foobar")
        self.assertTrue(u.verify_password('password1'))
        self.assertEqual(u.groups, [self.factory.default_group.id])

    def test_create_admin(self):
        runner = CliRunner()
        result = runner.invoke(
            create_user, ['foobar@example.com', 'Fred Foobar',
                          '--password', 'password1', '--admin'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        u = User.select().where(User.email == "foobar@example.com").first()
        self.assertEqual(u.name, "Fred Foobar")
        self.assertTrue(u.verify_password('password1'))
        self.assertEqual(u.groups, [self.factory.default_group.id,
                                    self.factory.admin_group.id])

    def test_create_googleauth(self):
        runner = CliRunner()
        result = runner.invoke(
            create_user, ['foobar@example.com', 'Fred Foobar', '--google'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        u = User.select().where(User.email == "foobar@example.com").first()
        self.assertEqual(u.name, "Fred Foobar")
        self.assertIsNone(u.password_hash)
        self.assertEqual(u.groups, [self.factory.default_group.id])

    def test_create_bad(self):
        self.factory.create_user(email='foobar@example.com')
        runner = CliRunner()
        result = runner.invoke(
            create_user, ['foobar@example.com', 'Fred Foobar'],
            input="password1\npassword1\n")
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('Failed', result.output)

    def test_delete(self):
        self.factory.create_user(email='foobar@example.com')
        ucount = User.select().count()
        runner = CliRunner()
        result = runner.invoke(
            delete_user, ['foobar@example.com'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(User.select().where(User.email ==
                                             "foobar@example.com").count(), 0)
        self.assertEqual(User.select().count(), ucount - 1)

    def test_delete_bad(self):
        ucount = User.select().count()
        runner = CliRunner()
        result = runner.invoke(
            delete_user, ['foobar@example.com'])
        self.assertIn('Deleted 0 users', result.output)
        self.assertEqual(User.select().count(), ucount)

    def test_password(self):
        self.factory.create_user(email='foobar@example.com')
        runner = CliRunner()
        result = runner.invoke(
            password, ['foobar@example.com', 'xyzzy'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        u = User.select().where(User.email == "foobar@example.com").first()
        self.assertTrue(u.verify_password('xyzzy'))

    def test_password_bad(self):
        runner = CliRunner()
        result = runner.invoke(
            password, ['foobar@example.com', 'xyzzy'])
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('not found', result.output)

    def test_password_bad_org(self):
        runner = CliRunner()
        result = runner.invoke(
            password, ['foobar@example.com', 'xyzzy', '--org', 'default'])
        self.assertTrue(result.exception)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('not found', result.output)

    def test_invite(self):
        admin = self.factory.create_user(email='redash-admin@example.com')
        runner = CliRunner()
        with mock.patch('redash.cli.users.invite_user') as iu:
            result = runner.invoke(
                invite, ['foobar@example.com', 'Fred Foobar',
                         'redash-admin@example.com'])
            self.assertFalse(result.exception)
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(iu.called)
            c = iu.call_args[0]
            self.assertEqual(c[0].id, self.factory.org.id)
            self.assertEqual(c[1].id, admin.id)
            self.assertEqual(c[2].email, 'foobar@example.com')


    def test_list(self):
        self.factory.create_user(name='Fred Foobar',
                                 email='foobar@example.com',
                                 organization=self.factory.org)
        runner = CliRunner()
        result = runner.invoke(list_user, [])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        output = """
        Id: 1
        Name: Fred Foobar
        Email: foobar@example.com
        Organization: Default
        """
        self.assertMultiLineEqual(result.output,
                                  textwrap.dedent(output).lstrip())

    def test_grant_admin(self):
        self.factory.create_user(name='Fred Foobar',
                                     email='foobar@example.com',
                                     org=self.factory.org,
                                     groups=[self.factory.default_group.id])
        runner = CliRunner()
        result = runner.invoke(
            grant_admin, ['foobar@example.com'])
        self.assertFalse(result.exception)
        self.assertEqual(result.exit_code, 0)
        u = User.select().order_by(User.id.desc()).first()
        self.assertEqual(u.groups, [self.factory.default_group.id,
                                    self.factory.admin_group.id])
