import type {
  // ChevronRight,
  LucideIcon,
} from 'lucide-react';
import { NavLink, useLocation } from 'react-router-dom';

import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
} from '@/components/shadcn/sidebar';

export function NavMain({
  items,
}: {
  items: {
    title: string;
    url: string;
    icon: LucideIcon;
    isActive?: boolean;
    items?: {
      title: string;
      url: string;
    }[];
  }[];
}) {
  const { pathname } = useLocation();

  return (
    <SidebarGroup>
      <SidebarGroupLabel>Create</SidebarGroupLabel>
      <SidebarMenu>
        {items.map((item) => (
          <SidebarMenu key={item.title}>
            <SidebarMenuButton asChild isActive={pathname === item.url}>
              <NavLink to={item.url}>
                <item.icon />
                <span>{item.title}</span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenu>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
