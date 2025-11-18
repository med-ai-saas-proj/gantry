import type {
  // ChevronRight,
  LucideIcon,
} from 'lucide-react';
import { NavLink, useLocation } from 'react-router-dom';

// import {
//   Collapsible,
//   CollapsibleContent,
//   CollapsibleTrigger,
// } from "@/components/shadcn/collapsible";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  // SidebarMenuItem,
  // SidebarMenuSub,
  // SidebarMenuSubButton,
  // SidebarMenuSubItem,
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
          // <Collapsible
          //   key={item.title}
          //   asChild
          //   defaultOpen={item.isActive}
          //   className="group/collapsible"
          // >
          //   <SidebarMenuItem>
          //     <CollapsibleTrigger asChild>
          //       <SidebarMenuButton tooltip={item.title}>
          //         {item.icon && <item.icon />}
          //         <span>{item.title}</span>
          //         <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
          //       </SidebarMenuButton>
          //     </CollapsibleTrigger>
          //     <CollapsibleContent>
          //       <SidebarMenuSub>
          //         {item.items?.map((subItem) => (
          //           <SidebarMenuSubItem key={subItem.title}>
          //             <SidebarMenuSubButton asChild>
          //               <a href={subItem.url}>
          //                 <span>{subItem.title}</span>
          //               </a>
          //             </SidebarMenuSubButton>
          //           </SidebarMenuSubItem>
          //         ))}
          //       </SidebarMenuSub>
          //     </CollapsibleContent>
          //   </SidebarMenuItem>
          // </Collapsible>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
