'use client';

import {
  AlignEndHorizontal,
  AudioLines,
  AudioWaveform,
  Bot,
  Command,
  Database,
  GalleryVerticalEnd,
  Image,
  KeyRound,
  MessageCircle,
  Network,
  SquareMenu,
  SquarePlay,
  SquareTerminal,
} from 'lucide-react';
import type * as React from 'react';

import { NavMain } from '@/components/nav-main';
import { NavProjects } from '@/components/nav-projects';
import { NavUser } from '@/components/nav-user';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from '@/components/shadcn/sidebar';
import { TeamSwitcher } from '@/components/team-switcher';

const data = {
  user: {
    name: 'shadcn',
    email: 'm@example.com',
    avatar: '/avatars/shadcn.jpg',
  },
  teams: [
    {
      name: 'Acme Inc',
      logo: GalleryVerticalEnd,
      plan: 'Enterprise',
    },
    {
      name: 'Acme Corp.',
      logo: AudioWaveform,
      plan: 'Startup',
    },
    {
      name: 'Evil Corp.',
      logo: Command,
      plan: 'Free',
    },
  ],
  navMain: [
    {
      title: 'Chat',
      url: '#',
      icon: MessageCircle,
    },
    {
      title: 'Agen builders',
      url: '#',
      icon: Network,
    },
    {
      title: 'Audio',
      url: '#',
      icon: AudioLines,
    },
    {
      title: 'Images',
      url: '#',
      icon: Image,
    },
    {
      title: 'Videos',
      url: '#',
      icon: SquarePlay,
    },
    {
      title: 'Assistants',
      url: '#',
      icon: Bot,
    },
  ],
  management: [
    {
      name: 'Usage',
      url: '#',
      icon: AlignEndHorizontal,
    },
    {
      name: 'API keys',
      url: '/api-keys',
      icon: KeyRound,
    },
    {
      name: 'Logs',
      url: '#',
      icon: SquareTerminal,
    },
    {
      name: 'Storage',
      url: '#',
      icon: Database,
    },
    {
      name: 'Batches',
      url: '#',
      icon: SquareMenu,
    },
  ],
};

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TeamSwitcher teams={data.teams} />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        <NavProjects projects={data.management} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
