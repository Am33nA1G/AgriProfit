export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
};

export type AuthStackParamList = {
  Login: undefined;
  OTP: { phoneNumber: string };
  ProfileComplete: undefined;
  PINSetup: undefined;
  PINVerify: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Prices: undefined;
  Transport: undefined;
  More: undefined;
  Admin: undefined;
};

export type PricesStackParamList = {
  CommodityList: undefined;
  CommodityDetail: { commodityId: string; commodityName: string };
  MandiDetail: { mandiId: string; mandiName: string };
};

export type CommunityStackParamList = {
  Posts: undefined;
  PostDetail: { postId: string };
  CreatePost: undefined;
};

export type MoreStackParamList = {
  MoreMenu: undefined;
  Inventory: undefined;
  AddInventory: undefined;
  Sales: undefined;
  AddSale: undefined;
  Community: undefined;
  Notifications: undefined;
  Profile: undefined;
  Settings: undefined;
};

export type AdminStackParamList = {
  AdminDashboard: undefined;
  Broadcast: undefined;
  AdminUsers: undefined;
  AdminPosts: undefined;
};
