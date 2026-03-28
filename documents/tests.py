from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Counterparty, ContractMaster, ProjectMaster


class CounterpartyListSortTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="tester", password="pass123456")
		profile = self.user.profile
		profile.can_manage_counterparty = True
		profile.save(update_fields=["can_manage_counterparty"])
		self.client.login(username="tester", password="pass123456")

	def _create_counterparty(self, name, idx):
		return Counterparty.objects.create(
			party_name=name,
			party_type="SUPPLIER",
			credit_code=f"91310110{idx:010d}",
			status="ACTIVE",
			created_by="tester",
			updated_by="tester",
		)

	def test_counterparty_list_sorts_by_pinyin_and_empty_last(self):
		names = ["张三", "阿里", "李四", "", "王五", "赵六"]
		for i, name in enumerate(names, start=1):
			self._create_counterparty(name, i)

		response = self.client.get(reverse("contract_counterparty_list"))
		self.assertEqual(response.status_code, 200)
		returned_names = [item.party_name for item in response.context["counterparties"]]
		self.assertEqual(returned_names, ["阿里", "李四", "王五", "张三", "赵六", ""])

	def test_counterparty_list_filter_keeps_same_sort_rule(self):
		names = ["张三公司", "阿里公司", "李四公司", ""]
		for i, name in enumerate(names, start=1):
			self._create_counterparty(name, i)

		response = self.client.get(reverse("contract_counterparty_list"), {"keyword": "公司"})
		self.assertEqual(response.status_code, 200)
		returned_names = [item.party_name for item in response.context["counterparties"]]
		self.assertEqual(returned_names, ["阿里公司", "李四公司", "张三公司"])

	def test_counterparty_pagination_is_stable_after_sorting(self):
		# 同名记录使用 id 作为最终排序键，确保分页边界稳定且不重叠。
		for i in range(1, 56):
			self._create_counterparty("测试公司", i)

		page1 = self.client.get(reverse("contract_counterparty_list"), {"page": 1})
		page2 = self.client.get(reverse("contract_counterparty_list"), {"page": 2})
		self.assertEqual(page1.status_code, 200)
		self.assertEqual(page2.status_code, 200)

		ids_page1 = [item.id for item in page1.context["counterparties"]]
		ids_page2 = [item.id for item in page2.context["counterparties"]]

		self.assertEqual(len(ids_page1), 50)
		self.assertEqual(len(ids_page2), 5)
		self.assertTrue(set(ids_page1).isdisjoint(set(ids_page2)))
		self.assertEqual(ids_page1, sorted(ids_page1))
		self.assertEqual(ids_page2, sorted(ids_page2))


class ContractListSortTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="contract_tester", password="pass123456")
		profile = self.user.profile
		profile.can_view_contract_ledger = True
		profile.save(update_fields=["can_view_contract_ledger"])
		self.client.login(username="contract_tester", password="pass123456")

		self.project = ProjectMaster.objects.create(
			project_code="PJ2026000001",
			project_name="测试项目",
			org_name="测试机构",
			province_code="310000",
			city_code="310100",
			business_unit="咨询",
			dept="D001",
			project_type="普通",
			org_mode="自营",
			data_status="正常",
			project_year="2026",
			status="启用",
			created_by="tester",
			updated_by="tester",
		)

	def _create_contract(self, idx, party_name):
		counterparty = Counterparty.objects.create(
			party_name=party_name,
			party_type="SUPPLIER",
			credit_code=f"91310120{idx:010d}",
			status="ACTIVE",
			created_by="tester",
			updated_by="tester",
		)
		return ContractMaster.objects.create(
			project=self.project,
			counterparty=counterparty,
			project_code_snapshot=self.project.project_code,
			contract_ct_code=f"CT20260000{idx:04d}",
			contract_name=f"合同{idx}",
			source_system="MANUAL",
			contract_direction="EXPENSE",
			contract_category="SERVICE",
			counterparty_name_snapshot=party_name,
			original_amount_tax=Decimal("100.00"),
			original_amount_notax=Decimal("90.00"),
			current_amount_tax=Decimal("100.00"),
			current_amount_notax=Decimal("90.00"),
			contract_status="SIGNED",
			created_by="tester",
			updated_by="tester",
		)

	def test_contract_list_sorts_by_counterparty_pinyin_and_empty_last(self):
		names = ["赵六", "", "李四", "阿里", "王五", "张三"]
		for i, name in enumerate(names, start=1):
			self._create_contract(i, name)

		response = self.client.get(reverse("contract_list"))
		self.assertEqual(response.status_code, 200)
		returned_names = [item.counterparty_name_snapshot for item in response.context["contracts"]]
		self.assertEqual(returned_names, ["阿里", "李四", "王五", "张三", "赵六", ""])

	def test_contract_list_filter_keeps_same_sort_rule(self):
		names = ["张三公司", "阿里公司", "李四公司", ""]
		for i, name in enumerate(names, start=1):
			self._create_contract(i, name)

		response = self.client.get(reverse("contract_list"), {"counterparty_name": "公司"})
		self.assertEqual(response.status_code, 200)
		returned_names = [item.counterparty_name_snapshot for item in response.context["contracts"]]
		self.assertEqual(returned_names, ["阿里公司", "李四公司", "张三公司"])

	def test_contract_list_pagination_is_stable_after_sorting(self):
		for i in range(1, 56):
			self._create_contract(i, "同名单位")

		page1 = self.client.get(reverse("contract_list"), {"page": 1})
		page2 = self.client.get(reverse("contract_list"), {"page": 2})
		self.assertEqual(page1.status_code, 200)
		self.assertEqual(page2.status_code, 200)

		ids_page1 = [item.id for item in page1.context["contracts"]]
		ids_page2 = [item.id for item in page2.context["contracts"]]

		self.assertEqual(len(ids_page1), 50)
		self.assertEqual(len(ids_page2), 5)
		self.assertTrue(set(ids_page1).isdisjoint(set(ids_page2)))
		self.assertEqual(ids_page1, sorted(ids_page1))
		self.assertEqual(ids_page2, sorted(ids_page2))
